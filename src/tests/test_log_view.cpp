/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A
 * PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

#include <gtest/gtest.h>

#include <set>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "failure_def.h"
#include "rack_error.h"

// 访问 LogView 私有成员 root_
#define private public
#include "log_view.h"
#undef private

#include "logger.h"

namespace {
// 打日志的库必须先初始化 log4cplus，否则 SEGFAULT
struct LoggerInit {
    LoggerInit() noexcept { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

// 构造一张调用图，同时维护 nodeIndex 与上下游邻接表
failure::graph::CallGraph MakeGraph(const std::vector<std::pair<std::string, std::string>> &nodes,
                                    const std::vector<std::pair<std::string, std::string>> &edges = {})
{
    failure::graph::CallGraph g;
    for (const auto &[name, comp] : nodes) {
        g.nodeIndex[name] = g.nodes.size();
        g.nodes.push_back({name, comp});
    }
    g.downstreamEdges.resize(g.nodes.size());
    g.upstreamEdges.resize(g.nodes.size());
    for (const auto &[src, dst] : edges) {
        g.edges.push_back({src, dst});
        g.downstreamEdges[g.nodeIndex[src]].push_back(g.nodeIndex[dst]);
        g.upstreamEdges[g.nodeIndex[dst]].push_back(g.nodeIndex[src]);
    }
    return g;
}

failure::FailureMetadata MakeMeta(const std::string &funcName)
{
    failure::FailureMetadata meta{};
    meta.funcName = funcName;
    return meta;
}

failure::FailureEvent MakeEvent(std::unordered_map<std::string, std::string> attrs)
{
    failure::FailureEvent ev{};
    ev.attributes = std::move(attrs);
    return ev;
}
} // namespace

// ---------- Build 基础行为 ----------

TEST(LogViewBuild, EmptyMetadataYieldsEmptyViews)
{
    failure::log::LogView view;
    auto graph = MakeGraph({{"main", "umq"}, {"func_a", "umq"}});
    EXPECT_EQ(view.Build({}, graph), RACK_OK);
    EXPECT_TRUE(view.root_["callstack_views"].isArray());
    EXPECT_EQ(view.root_["callstack_views"].size(), 0u);
    EXPECT_TRUE(view.root_["resource_views"].isArray());
    EXPECT_EQ(view.root_["resource_views"].size(), 0u);
}

// 图：main -> func_a -> func_b 的三函数链；元数据 funcName=func_b，事件覆盖三个函数。
// events 指针由用例设置（指向本结构成员，须在 RVO 落地后赋值）。
struct ChainCase {
    failure::graph::CallGraph graph;
    failure::FailureEvent evMain;
    failure::FailureEvent evA;
    failure::FailureEvent evA2;
    failure::FailureMetadata meta;
};

ChainCase MakeChainCase()
{
    ChainCase c;
    c.graph = MakeGraph({{"main", "umq"}, {"func_a", "umq"}, {"func_b", "umq"}},
                        {{"main", "func_a"}, {"func_a", "func_b"}});
    c.evMain = MakeEvent({{"function_name", "main"}, {"error_code", "E1"}});
    c.evA = MakeEvent({{"function_name", "func_a"}});
    c.evA2 = MakeEvent({{"function_name", "func_a"}, {"errno", "42"}});
    c.meta = MakeMeta("func_b");
    c.meta.threadId = "tid_b";
    c.meta.localEid = "eid_b";
    c.meta.localJettyId = "j1";
    c.meta.remoteEid = "re1";
    c.meta.remoteJettyId = "rj1";
    return c;
}

// 顶函数应解析为无上游命中的 main；节点/边视图按序构建
TEST(LogViewBuild, ResolvesTopFunctionAndBuildsCallstackView)
{
    ChainCase c = MakeChainCase();
    c.meta.events = {&c.evMain, &c.evA, &c.evA2, nullptr}; // 混入空指针验证跳过逻辑

    failure::log::LogView view;
    EXPECT_EQ(view.Build({c.meta}, c.graph), RACK_OK);
    ASSERT_EQ(view.root_["callstack_views"].size(), 1u);
    const Json::Value &cv = view.root_["callstack_views"][0];
    EXPECT_EQ(cv["top_function"].asString(), "main");

    // 节点按 viewId 排序：a / a#42 / b / main#E1
    ASSERT_EQ(cv["nodes"].size(), 4u);
    EXPECT_EQ(cv["nodes"][0]["id"].asString(), "func_a");
    EXPECT_TRUE(cv["nodes"][0]["error_code"].isNull());
    EXPECT_EQ(cv["nodes"][0]["hit_count"].asInt(), 1);
    EXPECT_EQ(cv["nodes"][0]["component"].asString(), "umq");
    EXPECT_EQ(cv["nodes"][0]["callstack_name"].asString(), "func_a");
    EXPECT_EQ(cv["nodes"][1]["id"].asString(), "func_a#42");
    EXPECT_EQ(cv["nodes"][1]["error_code"].asString(), "42");
    EXPECT_EQ(cv["nodes"][2]["id"].asString(), "func_b");
    EXPECT_EQ(cv["nodes"][3]["id"].asString(), "main#E1");
    EXPECT_EQ(cv["nodes"][3]["error_code"].asString(), "E1");

    // 边按 (src, dst) 排序；ratio = 边命中 / src 总命中
    ASSERT_EQ(cv["edges"].size(), 4u);
    EXPECT_EQ(cv["edges"][0]["src"].asString(), "func_a");
    EXPECT_EQ(cv["edges"][0]["dst"].asString(), "func_b");
    EXPECT_DOUBLE_EQ(cv["edges"][0]["ratio"].asDouble(), 1.0);
    EXPECT_EQ(cv["edges"][1]["src"].asString(), "func_a#42");
    EXPECT_DOUBLE_EQ(cv["edges"][1]["ratio"].asDouble(), 1.0);
    EXPECT_EQ(cv["edges"][2]["src"].asString(), "main#E1");
    EXPECT_EQ(cv["edges"][2]["dst"].asString(), "func_a");
    EXPECT_DOUBLE_EQ(cv["edges"][2]["ratio"].asDouble(), 0.5); // 1 / (1+1)
    EXPECT_EQ(cv["edges"][3]["dst"].asString(), "func_a#42");
    EXPECT_DOUBLE_EQ(cv["edges"][3]["ratio"].asDouble(), 0.5);
}

// 资源视图层级：tid -> eid -> jetty -> remote_jetty -> remote_eid
TEST(LogViewBuild, BuildsResourceViewHierarchy)
{
    ChainCase c = MakeChainCase();
    c.meta.events = {&c.evMain, &c.evA, &c.evA2, nullptr};

    failure::log::LogView view;
    EXPECT_EQ(view.Build({c.meta}, c.graph), RACK_OK);
    ASSERT_EQ(view.root_["resource_views"].size(), 1u);
    const Json::Value &rv = view.root_["resource_views"][0];
    EXPECT_EQ(rv["top_function"].asString(), "main");
    ASSERT_EQ(rv["tids"].size(), 1u);
    EXPECT_EQ(rv["tids"][0]["tid"].asString(), "tid_b");
    EXPECT_EQ(rv["tids"][0]["hit_count"].asInt(), 1);
    EXPECT_DOUBLE_EQ(rv["tids"][0]["ratio"].asDouble(), 1.0);
    ASSERT_EQ(rv["tids"][0]["eids"].size(), 1u);
    EXPECT_EQ(rv["tids"][0]["eids"][0]["eid"].asString(), "eid_b");
    const Json::Value &jetties = rv["tids"][0]["eids"][0]["jetty_ids"];
    ASSERT_EQ(jetties.size(), 1u);
    EXPECT_EQ(jetties[0]["jetty_id"].asString(), "j1");
    ASSERT_EQ(jetties[0]["remote_jetty_ids"].size(), 1u);
    EXPECT_EQ(jetties[0]["remote_jetty_ids"][0]["remote_jetty_id"].asString(), "rj1");
    ASSERT_EQ(jetties[0]["remote_jetty_ids"][0]["remote_eids"].size(), 1u);
    EXPECT_EQ(jetties[0]["remote_jetty_ids"][0]["remote_eids"][0]["remote_eid"].asString(), "re1");
}

TEST(LogViewBuild, CycleFallsBackToMetaFuncName)
{
    failure::log::LogView view;
    // 环：a -> b -> a，所有函数都有视图内上游
    auto graph = MakeGraph({{"func_a", "umq"}, {"func_b", "umq"}}, {{"func_a", "func_b"}, {"func_b", "func_a"}});
    failure::FailureEvent evA = MakeEvent({{"function_name", "func_a"}});
    failure::FailureEvent evB = MakeEvent({{"function_name", "func_b"}});
    auto meta = MakeMeta("func_a");
    meta.events = {&evA, &evB};

    EXPECT_EQ(view.Build({meta}, graph), RACK_OK);
    // 环内找不到顶函数 -> 回退到元数据自身的 funcName
    ASSERT_EQ(view.root_["callstack_views"].size(), 1u);
    EXPECT_EQ(view.root_["callstack_views"][0]["top_function"].asString(), "func_a");
}

TEST(LogViewBuild, UnknownFunctionsFallBackToMetaFuncName)
{
    failure::log::LogView view;
    auto graph = MakeGraph({{"main", "umq"}});
    // 事件函数不在图中 -> 无候选顶函数
    failure::FailureEvent evGhost = MakeEvent({{"function_name", "ghost"}});
    auto meta = MakeMeta("orphan");
    meta.events = {&evGhost};
    EXPECT_EQ(view.Build({meta}, graph), RACK_OK);
    ASSERT_EQ(view.root_["callstack_views"].size(), 1u);
    EXPECT_EQ(view.root_["callstack_views"][0]["top_function"].asString(), "orphan");
    // 图外函数不产生节点
    EXPECT_EQ(view.root_["callstack_views"][0]["nodes"].size(), 0u);

    // 空 funcName 且无事件 -> top_function 为 null（空串分支）
    failure::log::LogView view2;
    auto empty = MakeMeta("");
    EXPECT_EQ(view2.Build({empty}, graph), RACK_OK);
    ASSERT_EQ(view2.root_["callstack_views"].size(), 1u);
    EXPECT_TRUE(view2.root_["callstack_views"][0]["top_function"].isNull());
    EXPECT_TRUE(view2.root_["resource_views"][0]["top_function"].isNull());
}

TEST(LogViewBuild, ErrorCodePriorityAndCollection)
{
    failure::log::LogView view;
    auto graph = MakeGraph({{"func_a", "umq"}, {"func_b", "umq"}, {"func_c", "umq"}});
    // errno 优先于 code
    failure::FailureEvent evB = MakeEvent({{"function_name", "func_b"}, {"errno", "42"}, {"code", "99"}});
    // error_code 为空串时继续向后找
    failure::FailureEvent evC = MakeEvent({{"function_name", "func_c"}, {"error_code", ""}, {"code", "C7"}});
    // 与 meta.funcName 同名且带错误码 -> 擦除空错误码，仅保留 #E9
    failure::FailureEvent evA = MakeEvent({{"function_name", "func_a"}, {"error_code", "E9"}});
    // function_name 为空 -> 整个事件忽略
    failure::FailureEvent evEmpty = MakeEvent({{"function_name", ""}, {"code", "X"}});

    auto meta = MakeMeta("func_a");
    meta.events = {&evA, &evB, &evC, &evEmpty};
    EXPECT_EQ(view.Build({meta}, graph), RACK_OK);

    // 无边图：a/b/c 全部都是顶函数；meta.funcName=func_a 命中候选 -> 顶函数 func_a
    ASSERT_EQ(view.root_["callstack_views"].size(), 1u);
    const Json::Value &nodes = view.root_["callstack_views"][0]["nodes"];
    ASSERT_EQ(nodes.size(), 3u);
    // 排序后：func_a#E9 / func_b#42 / func_c#C7
    EXPECT_EQ(nodes[0]["id"].asString(), "func_a#E9");
    EXPECT_EQ(nodes[1]["id"].asString(), "func_b#42");
    EXPECT_EQ(nodes[1]["error_code"].asString(), "42");
    EXPECT_EQ(nodes[2]["id"].asString(), "func_c#C7");
    EXPECT_EQ(nodes[2]["error_code"].asString(), "C7");
    // func_a 不再有裸节点（空错误码被擦除）
}

TEST(LogViewBuild, DuplicateNodeNamesMergeIntoOneViewNode)
{
    failure::log::LogView view;
    // 两个同名节点（不同组件）：nodeKey 相同 -> 合并成一个视图节点，命中数累加，
    // 组件取先插入的下标较小的节点
    auto graph = MakeGraph({{"dup", "umq"}, {"other", "ubsocket"}, {"dup", "urma"}}, {{"dup", "other"}});
    auto meta = MakeMeta("dup");
    EXPECT_EQ(view.Build({meta}, graph), RACK_OK);

    const Json::Value &nodes = view.root_["callstack_views"][0]["nodes"];
    ASSERT_EQ(nodes.size(), 1u);
    EXPECT_EQ(nodes[0]["id"].asString(), "dup");
    EXPECT_EQ(nodes[0]["hit_count"].asInt(), 2);
    EXPECT_EQ(nodes[0]["component"].asString(), "umq");
    // other 不在命中集合 -> 无边
    EXPECT_EQ(view.root_["callstack_views"][0]["edges"].size(), 0u);
}

TEST(LogViewBuild, MergesRepeatedMetadata)
{
    failure::log::LogView view;
    auto graph = MakeGraph({{"func_a", "umq"}, {"func_b", "umq"}}, {{"func_a", "func_b"}});
    // 边的出现要求 src/dst 都在命中集合，因此给 func_b 也注入事件
    failure::FailureEvent evB = MakeEvent({{"function_name", "func_b"}});
    auto meta1 = MakeMeta("func_a");
    meta1.events = {&evB};
    auto meta2 = MakeMeta("func_a");
    meta2.events = {&evB};
    EXPECT_EQ(view.Build({meta1, meta2}, graph), RACK_OK);

    ASSERT_EQ(view.root_["callstack_views"].size(), 1u);
    const Json::Value &cv = view.root_["callstack_views"][0];
    ASSERT_EQ(cv["nodes"].size(), 2u);
    // 两次元数据命中累积
    EXPECT_EQ(cv["nodes"][0]["hit_count"].asInt(), 2);
    EXPECT_EQ(cv["nodes"][1]["hit_count"].asInt(), 2);
    ASSERT_EQ(cv["edges"].size(), 1u);
    EXPECT_EQ(cv["edges"][0]["hit_count"].asInt(), 2);
    EXPECT_DOUBLE_EQ(cv["edges"][0]["ratio"].asDouble(), 1.0);
    // 资源侧同样累积
    const Json::Value &rv = view.root_["resource_views"][0];
    ASSERT_EQ(rv["tids"].size(), 1u);
    EXPECT_EQ(rv["tids"][0]["hit_count"].asInt(), 2);
}

TEST(LogViewBuild, ResourceHierarchyWithRatios)
{
    failure::log::LogView view;
    auto graph = MakeGraph({{"func_a", "umq"}});

    auto meta1 = MakeMeta("func_a");
    meta1.threadId = "t1";
    meta1.localEid = "e1";
    meta1.localJettyId = "j1";
    meta1.remoteJettyId = "rj1";
    meta1.remoteEid = "re1";
    auto meta2 = MakeMeta("func_a");
    meta2.threadId = "t1";
    meta2.localEid = "e1";
    meta2.localJettyId = "j1";
    meta2.remoteJettyId = "rj1"; // remoteEid 为空 -> null
    auto meta3 = MakeMeta("func_a");
    meta3.threadId = "t1";
    meta3.localEid = "e2"; // jetty 为空 -> null
    auto meta4 = MakeMeta("func_a");
    meta4.threadId = "t2"; // 1/4
    meta4.localEid = "e1";
    meta4.localJettyId = "j1"; // 无远端 -> 空串 remote

    EXPECT_EQ(view.Build({meta1, meta2, meta3, meta4}, graph), RACK_OK);
    ASSERT_EQ(view.root_["resource_views"].size(), 1u);
    const Json::Value &tids = view.root_["resource_views"][0]["tids"];
    ASSERT_EQ(tids.size(), 2u);

    // t1：3 次 / 共 4 次
    EXPECT_EQ(tids[0]["tid"].asString(), "t1");
    EXPECT_EQ(tids[0]["hit_count"].asInt(), 3);
    EXPECT_DOUBLE_EQ(tids[0]["ratio"].asDouble(), 0.75);
    ASSERT_EQ(tids[0]["eids"].size(), 2u);
    // t1 下的 e1：2 次 / t1 共 3 次
    EXPECT_EQ(tids[0]["eids"][0]["eid"].asString(), "e1");
    EXPECT_EQ(tids[0]["eids"][0]["hit_count"].asInt(), 2);
    EXPECT_DOUBLE_EQ(tids[0]["eids"][0]["ratio"].asDouble(), 2.0 / 3.0);
    // e1 下的 j1 -> rj1 -> 空与 re1 两个远端 eid（空在前）
    const Json::Value &rjs = tids[0]["eids"][0]["jetty_ids"][0]["remote_jetty_ids"];
    ASSERT_EQ(rjs.size(), 1u);
    EXPECT_EQ(rjs[0]["remote_jetty_id"].asString(), "rj1");
    ASSERT_EQ(rjs[0]["remote_eids"].size(), 2u);
    EXPECT_TRUE(rjs[0]["remote_eids"][0]["remote_eid"].isNull());
    EXPECT_EQ(rjs[0]["remote_eids"][1]["remote_eid"].asString(), "re1");
    // t1 下的 e2：1 次，jetty 为空 -> null，远端也全空
    EXPECT_EQ(tids[0]["eids"][1]["eid"].asString(), "e2");
    EXPECT_DOUBLE_EQ(tids[0]["eids"][1]["ratio"].asDouble(), 1.0 / 3.0);
    const Json::Value &e2jetty = tids[0]["eids"][1]["jetty_ids"][0];
    EXPECT_TRUE(e2jetty["jetty_id"].isNull());
    EXPECT_TRUE(e2jetty["remote_jetty_ids"][0]["remote_jetty_id"].isNull());
    EXPECT_TRUE(e2jetty["remote_jetty_ids"][0]["remote_eids"][0]["remote_eid"].isNull());

    // t2：1 次，e1 占满
    EXPECT_EQ(tids[1]["tid"].asString(), "t2");
    EXPECT_EQ(tids[1]["hit_count"].asInt(), 1);
    EXPECT_DOUBLE_EQ(tids[1]["ratio"].asDouble(), 0.25);
    EXPECT_DOUBLE_EQ(tids[1]["eids"][0]["ratio"].asDouble(), 1.0);
}

TEST(LogViewBuild, RebuildResetsRoot)
{
    failure::log::LogView view;
    auto graph = MakeGraph({{"func_a", "umq"}});
    auto meta = MakeMeta("func_a");
    ASSERT_EQ(view.Build({meta}, graph), RACK_OK);
    EXPECT_EQ(view.root_["callstack_views"].size(), 1u);
    // 再次 Build 会重置 root_，旧数据不残留
    EXPECT_EQ(view.Build({}, graph), RACK_OK);
    EXPECT_EQ(view.root_["callstack_views"].size(), 0u);
    EXPECT_EQ(view.root_["resource_views"].size(), 0u);
}

// ---------- Dump（输出路径 /var/witty-ub 不可写） ----------

TEST(LogViewDump, FailsWhenVarDirUnwritable)
{
    failure::log::LogView view;
    auto graph = MakeGraph({{"func_a", "umq"}});
    auto meta = MakeMeta("func_a");
    ASSERT_EQ(view.Build({meta}, graph), RACK_OK);
    // 无法创建 /var/witty-ub -> 失败
    EXPECT_EQ(view.Dump(), RACK_FAIL);
}
