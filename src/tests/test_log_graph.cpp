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

#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#include "failure_def.h"
#include "rack_error.h"

// 访问 LogGraph 私有成员
#define private public
#include "log_graph.h"
#undef private

#include "logger.h"

// log_graph.cpp 中定义但未在头文件声明的自由函数，此处补充声明以便直测
namespace failure::log {
bool ParseEventType(const std::string &domain, EventTypeOption &eventType);
void SetKeyFunctionRole(const std::string &funcName, EventTypeOption eventType, KeyFuncRoleMap &keyFuncRoleMap);
} // namespace failure::log

namespace {
// 打日志的库必须先初始化 log4cplus，否则 SEGFAULT
struct LoggerInit {
    LoggerInit() { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

// 每个用例独立的临时目录，析构时清理
class TempDir {
public:
    TempDir()
    {
        static int counter = 0;
        dir_ = std::filesystem::temp_directory_path() /
               ("witty_log_graph_test_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) +
                "_" + std::to_string(counter++));
        std::filesystem::create_directories(dir_);
    }
    ~TempDir() { std::filesystem::remove_all(dir_); }
    const std::filesystem::path &Path() const { return dir_; }

private:
    std::filesystem::path dir_;
};

void WriteFile(const std::filesystem::path &path, const std::string &content)
{
    std::ofstream out(path);
    out << content;
}

// 构造一张 6 节点菱形图：main -> {a, b} -> c -> {d, e}，d -> e
Json::Value MakeDiamondRoot()
{
    Json::Value root;
    Json::Value nodes(Json::arrayValue);
    const char *names[] = {"main", "func_a", "func_b", "func_c", "func_d", "func_e"};
    for (const char *name : names) {
        Json::Value node;
        node["name"] = name;
        node["component"] = "umq";
        nodes.append(node);
    }
    root["nodes"] = nodes;

    Json::Value edges(Json::arrayValue);
    auto addEdge = [&edges](const char *src, const char *dst) {
        Json::Value edge;
        edge["src"] = src;
        edge["dst"] = dst;
        edges.append(edge);
    };
    addEdge("main", "func_a");
    addEdge("main", "func_b");
    addEdge("func_a", "func_c");
    addEdge("func_b", "func_c");
    addEdge("func_c", "func_d");
    addEdge("func_c", "func_e");
    addEdge("func_d", "func_e");
    root["edges"] = edges;
    return root;
}
} // namespace

// ---------- 自由函数 ParseEventType ----------

TEST(ParseEventType, AllValidDomains)
{
    failure::EventTypeOption ev;
    // bind -> BIND
    EXPECT_TRUE(failure::log::ParseEventType("bind", ev));
    EXPECT_EQ(ev, failure::EventTypeOption::BIND);
    // unbind -> UNBIND
    EXPECT_TRUE(failure::log::ParseEventType("unbind", ev));
    EXPECT_EQ(ev, failure::EventTypeOption::UNBIND);
    // post / poll -> POST
    EXPECT_TRUE(failure::log::ParseEventType("post", ev));
    EXPECT_EQ(ev, failure::EventTypeOption::POST);
    EXPECT_TRUE(failure::log::ParseEventType("poll", ev));
    EXPECT_EQ(ev, failure::EventTypeOption::POST);
}

TEST(ParseEventType, RejectsInvalidDomain)
{
    failure::EventTypeOption ev = failure::EventTypeOption::POST;
    EXPECT_FALSE(failure::log::ParseEventType("unknown", ev));
    EXPECT_FALSE(failure::log::ParseEventType("", ev));
    EXPECT_FALSE(failure::log::ParseEventType("Bind", ev)); // 大小写敏感
}

// ---------- 自由函数 SetKeyFunctionRole ----------

TEST(SetKeyFunctionRole, AssignsTxRxNullForPost)
{
    failure::KeyFuncRoleMap roles;
    // 函数名含 tx -> tx
    failure::log::SetKeyFunctionRole("umq_ub_post_tx", failure::EventTypeOption::POST, roles);
    EXPECT_EQ(roles["umq_ub_post_tx"], "tx");
    // 函数名含 rx -> rx
    failure::log::SetKeyFunctionRole("umq_ub_poll_rx", failure::EventTypeOption::POST, roles);
    EXPECT_EQ(roles["umq_ub_poll_rx"], "rx");
    // 既不含 tx 也不含 rx -> null
    failure::log::SetKeyFunctionRole("umq_ub_connect_jetty", failure::EventTypeOption::POST, roles);
    EXPECT_EQ(roles["umq_ub_connect_jetty"], "null");
    EXPECT_EQ(roles.size(), 3u);
}

TEST(SetKeyFunctionRole, SkipsNonPostEvent)
{
    failure::KeyFuncRoleMap roles;
    // 非 POST 事件不写角色表
    failure::log::SetKeyFunctionRole("umq_ub_post_tx", failure::EventTypeOption::BIND, roles);
    failure::log::SetKeyFunctionRole("umq_ub_unbind_impl", failure::EventTypeOption::UNBIND, roles);
    EXPECT_TRUE(roles.empty());
}

// ---------- ReadJson ----------

TEST(LogGraphReadJson, FailsOnMissingFile)
{
    failure::log::LogGraph graph;
    Json::Value root;
    TempDir dir;
    // 文件不存在 -> 打开失败
    EXPECT_EQ(graph.ReadJson(root, (dir.Path() / "no_such.json").string()), RACK_FAIL);
}

TEST(LogGraphReadJson, FailsOnInvalidJson)
{
    failure::log::LogGraph graph;
    Json::Value root;
    TempDir dir;
    auto path = dir.Path() / "bad.json";
    WriteFile(path, "{not a valid json");
    // 内容非法 -> 解析失败
    EXPECT_EQ(graph.ReadJson(root, path.string()), RACK_FAIL);
}

TEST(LogGraphReadJson, FailsOnNonObjectRoot)
{
    failure::log::LogGraph graph;
    Json::Value root;
    TempDir dir;
    auto path = dir.Path() / "array.json";
    WriteFile(path, "[1, 2, 3]");
    // 根节点不是对象 -> 失败
    EXPECT_EQ(graph.ReadJson(root, path.string()), RACK_FAIL);
}

TEST(LogGraphReadJson, SucceedsOnValidObject)
{
    failure::log::LogGraph graph;
    Json::Value root;
    TempDir dir;
    auto path = dir.Path() / "ok.json";
    WriteFile(path, "{\"nodes\": [], \"edges\": []}");
    EXPECT_EQ(graph.ReadJson(root, path.string()), RACK_OK);
    EXPECT_TRUE(root.isObject());
    EXPECT_TRUE(root["nodes"].isArray());
}

// ---------- ValidateGraphRoot ----------

TEST(LogGraphValidateRoot, AcceptsArrayNodesAndEdges)
{
    failure::log::LogGraph graph;
    const Json::Value *nodes = nullptr;
    const Json::Value *edges = nullptr;
    Json::Value root = MakeDiamondRoot();
    EXPECT_EQ(graph.ValidateGraphRoot(root, nodes, edges), RACK_OK);
    ASSERT_NE(nodes, nullptr);
    ASSERT_NE(edges, nullptr);
    EXPECT_EQ(nodes->size(), 6u);
    EXPECT_EQ(edges->size(), 7u);
}

TEST(LogGraphValidateRoot, RejectsMissingOrNonArray)
{
    failure::log::LogGraph graph;
    const Json::Value *nodes = nullptr;
    const Json::Value *edges = nullptr;

    // 缺少 nodes/edges 键 -> 取到 null，非数组 -> 失败
    Json::Value emptyRoot;
    EXPECT_EQ(graph.ValidateGraphRoot(emptyRoot, nodes, edges), RACK_FAIL);

    // nodes 非数组
    Json::Value badNodes;
    badNodes["nodes"] = "not_array";
    badNodes["edges"] = Json::arrayValue;
    EXPECT_EQ(graph.ValidateGraphRoot(badNodes, nodes, edges), RACK_FAIL);

    // edges 非数组
    Json::Value badEdges;
    badEdges["nodes"] = Json::arrayValue;
    badEdges["edges"] = 123;
    EXPECT_EQ(graph.ValidateGraphRoot(badEdges, nodes, edges), RACK_FAIL);
}

// ---------- BuildNodes ----------

TEST(LogGraphBuildNodes, BuildsNodesAndIndex)
{
    failure::log::LogGraph graph;
    Json::Value root = MakeDiamondRoot();
    failure::graph::CallGraph built;
    EXPECT_EQ(graph.BuildNodes(root["nodes"], built), RACK_OK);
    ASSERT_EQ(built.nodes.size(), 6u);
    EXPECT_EQ(built.nodes[0].name, "main");
    EXPECT_EQ(built.nodes[0].component, "umq");
    EXPECT_EQ(built.nodes[3].name, "func_c");
    // 索引与邻接表已按节点数初始化
    EXPECT_EQ(built.nodeIndex.size(), 6u);
    EXPECT_EQ(built.nodeIndex["func_c"], 3u);
    EXPECT_EQ(built.downstreamEdges.size(), 6u);
    EXPECT_EQ(built.upstreamEdges.size(), 6u);
}

TEST(LogGraphBuildNodes, RejectsInvalidItems)
{
    failure::log::LogGraph graph;
    failure::graph::CallGraph built;

    // 非对象节点
    Json::Value nonObj(Json::arrayValue);
    nonObj.append(1);
    EXPECT_EQ(graph.BuildNodes(nonObj, built), RACK_FAIL);

    // 空 name
    Json::Value emptyName(Json::arrayValue);
    Json::Value node1;
    node1["name"] = "";
    node1["component"] = "umq";
    emptyName.append(node1);
    EXPECT_EQ(graph.BuildNodes(emptyName, built), RACK_FAIL);

    // 重复 name
    Json::Value dup(Json::arrayValue);
    Json::Value node2;
    node2["name"] = "same";
    dup.append(node2);
    dup.append(node2);
    EXPECT_EQ(graph.BuildNodes(dup, built), RACK_FAIL);
}

// ---------- BuildEdges ----------

TEST(LogGraphBuildEdges, BuildsEdgesAndAdjacency)
{
    failure::log::LogGraph graph;
    Json::Value root = MakeDiamondRoot();
    failure::graph::CallGraph built;
    ASSERT_EQ(graph.BuildNodes(root["nodes"], built), RACK_OK);
    ASSERT_EQ(graph.BuildEdges(root["edges"], built), RACK_OK);

    ASSERT_EQ(built.edges.size(), 7u);
    EXPECT_EQ(built.edges[2].src, "func_a");
    EXPECT_EQ(built.edges[2].dst, "func_c");
    // 下游邻接表：func_c(3) -> func_d(4), func_e(5)
    ASSERT_EQ(built.downstreamEdges[3].size(), 2u);
    EXPECT_EQ(built.downstreamEdges[3][0], 4u);
    EXPECT_EQ(built.downstreamEdges[3][1], 5u);
    // 上游邻接表：func_c(3) <- func_a(1), func_b(2)
    ASSERT_EQ(built.upstreamEdges[3].size(), 2u);
    EXPECT_EQ(built.upstreamEdges[3][0], 1u);
    EXPECT_EQ(built.upstreamEdges[3][1], 2u);
}

TEST(LogGraphBuildEdges, SkipsInvalidButKeepsGoing)
{
    failure::log::LogGraph graph;
    Json::Value root = MakeDiamondRoot();
    failure::graph::CallGraph built;
    ASSERT_EQ(graph.BuildNodes(root["nodes"], built), RACK_OK);

    Json::Value edges(Json::arrayValue);
    // 空 src：跳过
    Json::Value emptySrc;
    emptySrc["src"] = "";
    emptySrc["dst"] = "func_a";
    edges.append(emptySrc);
    // 空 dst：跳过
    Json::Value emptyDst;
    emptyDst["src"] = "func_a";
    emptyDst["dst"] = "";
    edges.append(emptyDst);
    // 悬挂边（节点不存在）：跳过
    Json::Value dangling;
    dangling["src"] = "no_such_node";
    dangling["dst"] = "func_a";
    edges.append(dangling);
    // 合法边：保留
    Json::Value valid;
    valid["src"] = "main";
    valid["dst"] = "func_c";
    edges.append(valid);

    EXPECT_EQ(graph.BuildEdges(edges, built), RACK_OK);
    ASSERT_EQ(built.edges.size(), 1u);
    EXPECT_EQ(built.edges[0].src, "main");
    ASSERT_EQ(built.downstreamEdges[0].size(), 1u);
    EXPECT_EQ(built.downstreamEdges[0][0], 3u);
}

TEST(LogGraphBuildEdges, RejectsNonObjectEdge)
{
    failure::log::LogGraph graph;
    Json::Value root = MakeDiamondRoot();
    failure::graph::CallGraph built;
    ASSERT_EQ(graph.BuildNodes(root["nodes"], built), RACK_OK);

    Json::Value edges(Json::arrayValue);
    edges.append("not_an_object");
    EXPECT_EQ(graph.BuildEdges(edges, built), RACK_FAIL);
}

// ---------- BuildGraph ----------

TEST(LogGraphBuildGraph, BuildsFullGraph)
{
    failure::log::LogGraph graph;
    Json::Value root = MakeDiamondRoot();
    failure::graph::CallGraph built;
    EXPECT_EQ(graph.BuildGraph(root, built), RACK_OK);
    EXPECT_EQ(built.nodes.size(), 6u);
    EXPECT_EQ(built.edges.size(), 7u);
}

TEST(LogGraphBuildGraph, RejectsInvalidRoot)
{
    failure::log::LogGraph graph;
    Json::Value root;
    root["nodes"] = "bad";
    root["edges"] = Json::arrayValue;
    failure::graph::CallGraph built;
    // 根非法 -> 失败且不清空入参图（提前返回）
    EXPECT_EQ(graph.BuildGraph(root, built), RACK_FAIL);
}

// ---------- 硬编码路径的加载入口（仅失败分支可达） ----------

TEST(LogGraphLoad, CallstackFailsWhenFileMissing)
{
    failure::log::LogGraph graph;
    // /var/witty-ub/callstack-analysis/overall_callstack.json 不可达 -> 失败
    EXPECT_EQ(graph.LoadCallstack(), RACK_FAIL);
}

TEST(LogGraphLoad, KeyFunctionsFailsWhenFileMissing)
{
    failure::log::LogGraph graph;
    // /var/witty-ub/keyfunc-analysis/keyfunc.json 不可达 -> 失败
    EXPECT_EQ(graph.LoadKeyFunctions(), RACK_FAIL);
}

// ---------- FindNodesByName ----------

TEST(LogGraphFindNodes, EmptyGraphKeepsInput)
{
    failure::log::LogGraph graph;
    std::vector<failure::graph::FuncNode> matched;
    failure::graph::FuncNode pre;
    pre.name = "pre";
    matched.push_back(pre);
    // 空图提前返回，不清空入参
    graph.FindNodesByName("any", matched);
    ASSERT_EQ(matched.size(), 1u);
    EXPECT_EQ(matched[0].name, "pre");
}

TEST(LogGraphFindNodes, MatchesAllSameNameAndClearsFirst)
{
    failure::log::LogGraph graph;
    Json::Value root = MakeDiamondRoot();
    ASSERT_EQ(graph.BuildGraph(root, graph.graph_), RACK_OK);

    std::vector<failure::graph::FuncNode> matched;
    failure::graph::FuncNode stale;
    stale.name = "stale";
    matched.push_back(stale);

    graph.FindNodesByName("func_c", matched);
    ASSERT_EQ(matched.size(), 1u);
    EXPECT_EQ(matched[0].name, "func_c");
    EXPECT_EQ(matched[0].component, "umq");

    // 无匹配 -> 清空
    graph.FindNodesByName("no_such_func", matched);
    EXPECT_TRUE(matched.empty());
}

// ---------- FindNeighborhood ----------

TEST(LogGraphNeighborhood, EmptyGraphAndUnknownName)
{
    failure::log::LogGraph graph;
    std::vector<failure::graph::FuncNode> up;
    std::vector<failure::graph::FuncNode> down;
    // 空图：直接返回，不崩溃
    graph.FindNeighborhood("func_c", up, down);
    EXPECT_TRUE(up.empty());
    EXPECT_TRUE(down.empty());

    Json::Value root = MakeDiamondRoot();
    ASSERT_EQ(graph.BuildGraph(root, graph.graph_), RACK_OK);
    // 图中不存在的名字：告警后返回
    graph.FindNeighborhood("no_such_func", up, down);
    EXPECT_TRUE(up.empty());
    EXPECT_TRUE(down.empty());
}

TEST(LogGraphNeighborhood, CollectsSortedUpAndDownstream)
{
    failure::log::LogGraph graph;
    Json::Value root = MakeDiamondRoot();
    ASSERT_EQ(graph.BuildGraph(root, graph.graph_), RACK_OK);

    std::vector<failure::graph::FuncNode> up;
    std::vector<failure::graph::FuncNode> down;
    graph.FindNeighborhood("func_c", up, down);
    // 上游：main(0), func_a(1), func_b(2)，按节点下标排序
    ASSERT_EQ(up.size(), 3u);
    EXPECT_EQ(up[0].name, "main");
    EXPECT_EQ(up[1].name, "func_a");
    EXPECT_EQ(up[2].name, "func_b");
    // 下游：func_d(4), func_e(5)
    ASSERT_EQ(down.size(), 2u);
    EXPECT_EQ(down[0].name, "func_d");
    EXPECT_EQ(down[1].name, "func_e");
}

TEST(LogGraphNeighborhood, LeafNodeHasEmptyNeighborhood)
{
    failure::log::LogGraph graph;
    Json::Value root = MakeDiamondRoot();
    ASSERT_EQ(graph.BuildGraph(root, graph.graph_), RACK_OK);

    std::vector<failure::graph::FuncNode> up;
    std::vector<failure::graph::FuncNode> down;
    // main 无上游，只有下游
    graph.FindNeighborhood("main", up, down);
    EXPECT_TRUE(up.empty());
    ASSERT_EQ(down.size(), 5u);

    // 注意：FindNeighborhood 对入参是追加而非清空，两次查询需用新向量。
    // func_e 无下游，上游含 main/a/b/c/d 共 5 个
    std::vector<failure::graph::FuncNode> up2;
    std::vector<failure::graph::FuncNode> down2;
    graph.FindNeighborhood("func_e", up2, down2);
    EXPECT_TRUE(down2.empty());
    ASSERT_EQ(up2.size(), 5u); // main/a/b/c/d 均可达
}

// ---------- InitKeyFuncMap ----------

TEST(LogGraphInitKeyFuncMap, RejectsInvalidInput)
{
    failure::log::LogGraph graph;
    failure::KeyFuncEventTypeMap eventTypeMap;
    failure::KeyFuncRoleMap roleMap;

    // functions 缺失/非数组
    Json::Value noFunc;
    EXPECT_EQ(graph.InitKeyFuncMap(noFunc, eventTypeMap, roleMap), RACK_FAIL);
    Json::Value badFunc;
    badFunc["functions"] = "not_array";
    EXPECT_EQ(graph.InitKeyFuncMap(badFunc, eventTypeMap, roleMap), RACK_FAIL);

    // 非对象条目
    Json::Value nonObjRoot;
    Json::Value nonObjArr(Json::arrayValue);
    nonObjArr.append(1);
    nonObjRoot["functions"] = nonObjArr;
    EXPECT_EQ(graph.InitKeyFuncMap(nonObjRoot, eventTypeMap, roleMap), RACK_FAIL);

    // 空 name
    Json::Value emptyNameRoot;
    Json::Value arr1(Json::arrayValue);
    Json::Value f1;
    f1["name"] = "";
    f1["domain"] = "bind";
    arr1.append(f1);
    emptyNameRoot["functions"] = arr1;
    EXPECT_EQ(graph.InitKeyFuncMap(emptyNameRoot, eventTypeMap, roleMap), RACK_FAIL);

    // 空 domain
    Json::Value emptyDomainRoot;
    Json::Value arr2(Json::arrayValue);
    Json::Value f2;
    f2["name"] = "umq_ub_post_tx";
    f2["domain"] = "";
    arr2.append(f2);
    emptyDomainRoot["functions"] = arr2;
    EXPECT_EQ(graph.InitKeyFuncMap(emptyDomainRoot, eventTypeMap, roleMap), RACK_FAIL);

    // 非法 domain
    Json::Value badDomainRoot;
    Json::Value arr3(Json::arrayValue);
    Json::Value f3;
    f3["name"] = "umq_ub_post_tx";
    f3["domain"] = "unknown";
    arr3.append(f3);
    badDomainRoot["functions"] = arr3;
    EXPECT_EQ(graph.InitKeyFuncMap(badDomainRoot, eventTypeMap, roleMap), RACK_FAIL);
}

TEST(LogGraphInitKeyFuncMap, ParsesAllDomainsAndRoles)
{
    failure::log::LogGraph graph;
    failure::KeyFuncEventTypeMap eventTypeMap;
    failure::KeyFuncRoleMap roleMap;

    Json::Value root;
    Json::Value functions(Json::arrayValue);
    auto addFunc = [&functions](const char *name, const char *domain) {
        Json::Value f;
        f["name"] = name;
        f["domain"] = domain;
        functions.append(f);
    };
    addFunc("umq_ub_bind_inner_impl", "bind");
    addFunc("umq_ub_unbind_impl", "unbind");
    addFunc("umq_ub_post_tx", "post");
    addFunc("umq_ub_poll_rx", "poll");
    addFunc("umq_ub_connect_jetty", "post");
    root["functions"] = functions;

    EXPECT_EQ(graph.InitKeyFuncMap(root, eventTypeMap, roleMap), RACK_OK);
    EXPECT_EQ(eventTypeMap.size(), 5u);
    EXPECT_EQ(eventTypeMap["umq_ub_bind_inner_impl"], failure::EventTypeOption::BIND);
    EXPECT_EQ(eventTypeMap["umq_ub_unbind_impl"], failure::EventTypeOption::UNBIND);
    EXPECT_EQ(eventTypeMap["umq_ub_post_tx"], failure::EventTypeOption::POST);
    EXPECT_EQ(eventTypeMap["umq_ub_poll_rx"], failure::EventTypeOption::POST);
    // 角色表只记录 POST 事件
    EXPECT_EQ(roleMap.size(), 3u);
    EXPECT_EQ(roleMap["umq_ub_post_tx"], "tx");
    EXPECT_EQ(roleMap["umq_ub_poll_rx"], "rx");
    EXPECT_EQ(roleMap["umq_ub_connect_jetty"], "null");
}

// ---------- InitKeyFuncRelevance ----------

TEST(LogGraphRelevance, BuildsRelevanceMapFromGraph)
{
    failure::log::LogGraph graph;
    Json::Value root = MakeDiamondRoot();
    ASSERT_EQ(graph.BuildGraph(root, graph.graph_), RACK_OK);
    // 直接注入关键函数事件表（绕过硬编码路径的 LoadKeyFunctions）
    graph.keyFuncEventTypeMap_["func_c"] = failure::EventTypeOption::POST;
    graph.keyFuncEventTypeMap_["func_d"] = failure::EventTypeOption::BIND;

    EXPECT_EQ(graph.InitKeyFuncRelevance(), RACK_OK);
    const auto &relevance = graph.GetKeyFuncRelevanceMap();
    ASSERT_EQ(relevance.size(), 2u);
    ASSERT_NE(relevance.find("func_c"), relevance.end());
    // func_c 上游 3 个、下游 2 个
    EXPECT_EQ(relevance.at("func_c").upstreamFuncs.size(), 3u);
    EXPECT_EQ(relevance.at("func_c").downstreamFuncs.size(), 2u);
    // 名字索引与向量对齐
    EXPECT_EQ(relevance.at("func_c").upstreamNameIndex.size(), 3u);
    EXPECT_EQ(relevance.at("func_c").downstreamNameIndex.size(), 2u);
    // func_d 上游 4 个（main/a/b/c），下游 1 个（func_e）
    ASSERT_NE(relevance.find("func_d"), relevance.end());
    EXPECT_EQ(relevance.at("func_d").upstreamFuncs.size(), 4u);
    EXPECT_EQ(relevance.at("func_d").downstreamFuncs.size(), 1u);
}

TEST(LogGraphRelevance, EmptyKeyFuncsYieldsEmptyMap)
{
    failure::log::LogGraph graph;
    // 事件表为空 -> 空关联表，返回 OK
    EXPECT_EQ(graph.InitKeyFuncRelevance(), RACK_OK);
    EXPECT_TRUE(graph.GetKeyFuncRelevanceMap().empty());
}

// ---------- Getter ----------

TEST(LogGraphGetters, ExposeInternalState)
{
    failure::log::LogGraph graph;
    Json::Value root = MakeDiamondRoot();
    ASSERT_EQ(graph.BuildGraph(root, graph.graph_), RACK_OK);
    graph.keyFuncEventTypeMap_["func_c"] = failure::EventTypeOption::POST;
    graph.keyFuncRoleMap_["func_c"] = "tx";

    EXPECT_EQ(graph.GetCallGraph().nodes.size(), 6u);
    EXPECT_EQ(graph.GetKeyFuncEventTypeMap().at("func_c"), failure::EventTypeOption::POST);
    EXPECT_EQ(graph.GetKeyFuncRoleMap().at("func_c"), "tx");
    EXPECT_TRUE(graph.GetKeyFuncRelevanceMap().empty());
}
