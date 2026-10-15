/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 * PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

#include <gtest/gtest.h>

#include <sys/stat.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <map>
#include <string>
#include <vector>

#include "temp_dir.h"
#include "logger.h"
#include "ubse_context.h"
#include "urma_topology.h"
#include "witty_json_module.h"

namespace urma::topo {
// urma_topology.cpp 中的内部自由函数（外部链接），直接前向声明进行直测
bool ParseLogLine(const std::string &line, SessionKey &key);
} // namespace urma::topo

namespace {

// urma_topology 全链路会打日志，且 URMATopology 构造时从 UbseContext 单例取 JSONModule；
// 必须先初始化 log4cplus 并注册 JSONModule，否则 CreateTopology 写文件时解引用空指针崩溃。
struct EnvInit {
    EnvInit() noexcept
    {
        rack::logger::init(nullptr);
        auto module = std::make_shared<witty_json::module::JSONModule>();
        module->Initialize();
        ubse::context::UbseContext::GetInstance().InitModule<witty_json::module::JSONModule>(module);
    }
};
static EnvInit g_envInit;

// 每用例独立临时目录（公共实现见 temp_dir.h）

// 标准格式的 umq 会话日志行
std::string BindLine(const std::string &localEid, const std::string &localJetty, const std::string &remoteEid,
                     const std::string &remoteJetty)
{
    return "umq: bind jetty success, local eid: " + localEid + ", local jetty_id: " + localJetty +
           ", remote eid: " + remoteEid + ", remote jetty_id: " + remoteJetty;
}

std::string UnbindLine(const std::string &localEid, const std::string &localJetty, const std::string &remoteEid,
                       const std::string &remoteJetty)
{
    return "umq: unbind jetty, local eid: " + localEid + ", local jetty_id: " + localJetty +
           ", remote eid: " + remoteEid + ", remote jetty_id: " + remoteJetty;
}

ubse::context::TopoToolsArgs MakeArgs(const std::string &podMode, const std::map<std::string, std::string> &logMap,
                                      const std::vector<std::string> &podList = {})
{
    ubse::context::TopoToolsArgs args;
    args.networkMode = "fullmesh";
    args.podMode = podMode;
    args.umq_log_path_map = logMap;
    args.pod_id_list = podList;
    return args;
}

} // namespace

// ---------------------------------------------------------------------------
// ParseLogLine：正则提取四元组
// ---------------------------------------------------------------------------

TEST(ParseLogLine, ExtractsSessionFields)
{
    urma::topo::SessionKey key;
    // eid 为冒号分隔的十六进制（正则字符类 [0-9a-fA-F:]+ 不接受 0x 前缀）
    ASSERT_TRUE(urma::topo::ParseLogLine(
        "2024-01-15 umq: bind jetty success, local eid: 12:34, local jetty_id: 5, remote eid: 56:78, "
        "remote jetty_id: 9",
        key));
    EXPECT_EQ(key.localEid, "12:34");
    EXPECT_EQ(key.localJettyId, "5");
    EXPECT_EQ(key.remoteEid, "56:78");
    EXPECT_EQ(key.remoteJettyId, "9");
}

TEST(ParseLogLine, RejectsMalformedLines)
{
    urma::topo::SessionKey key;
    // 缺少 remote jetty_id
    EXPECT_FALSE(urma::topo::ParseLogLine("local eid: 0x1, local jetty_id: 2, remote eid: 0x3", key));
    // 完全不相关的内容
    EXPECT_FALSE(urma::topo::ParseLogLine("nothing to parse here", key));
    // 空行
    EXPECT_FALSE(urma::topo::ParseLogLine("", key));
}

// ---------------------------------------------------------------------------
// SessionKey：排序与字符串化
// ---------------------------------------------------------------------------

TEST(SessionKey, OrdersByFieldsInSequence)
{
    // 依次按 localEid、localJettyId、remoteEid、remoteJettyId 排序
    urma::topo::SessionKey a;
    a.localEid = "1";
    a.localJettyId = "1";
    a.remoteEid = "1";
    a.remoteJettyId = "1";
    urma::topo::SessionKey b = a;
    b.localEid = "2";
    EXPECT_TRUE(a < b);

    urma::topo::SessionKey c = a;
    c.localJettyId = "2";
    EXPECT_TRUE(a < c);

    urma::topo::SessionKey d = a;
    d.remoteEid = "2";
    EXPECT_TRUE(a < d);

    urma::topo::SessionKey e = a;
    e.remoteJettyId = "2";
    EXPECT_TRUE(a < e);

    // 完全相等则不满足严格序
    EXPECT_FALSE(a < a);
}

TEST(SessionKey, ToStringContainsAllFields)
{
    urma::topo::SessionKey key;
    key.localEid = "le";
    key.localJettyId = "lj";
    key.remoteEid = "re";
    key.remoteJettyId = "rj";
    const std::string text = key.ToString();
    EXPECT_NE(text.find("local eid=le"), std::string::npos);
    EXPECT_NE(text.find("local jetty_id=lj"), std::string::npos);
    EXPECT_NE(text.find("remote eid=re"), std::string::npos);
    EXPECT_NE(text.find("remote jetty_id=rj"), std::string::npos);
}

// ---------------------------------------------------------------------------
// ParseUMQLog：日志收集与会话跟踪
// ---------------------------------------------------------------------------

TEST(URMATopologyParseUMQLog, MissingPathFails)
{
    urma::topo::URMATopology topo;
    std::map<urma::topo::SessionKey, std::string> sessions;
    EXPECT_EQ(topo.ParseUMQLog("/nonexistent/witty/umq/log", sessions), urma::URMA_FAIL);
}

TEST(URMATopologyParseUMQLog, TracksBindAndUnbindSessions)
{
    TempDir dir;
    std::string path = dir.Write("umq.log",
        BindLine("1", "1", "2", "2") + "\n" +
        "unrelated line without keywords\n" +
        "\n" + // 空行应跳过
        BindLine("3", "3", "4", "4") + "\n" +
        UnbindLine("1", "1", "2", "2") + "\n");

    urma::topo::URMATopology topo;
    std::map<urma::topo::SessionKey, std::string> sessions;
    ASSERT_EQ(topo.ParseUMQLog(path, sessions), urma::URMA_SUCCESS);
    // 会话 (1,1,2,2) 被 unbind 删除，仅剩 (3,3,4,4)
    ASSERT_EQ(sessions.size(), 1u);
    urma::topo::SessionKey expected;
    expected.localEid = "3";
    expected.localJettyId = "3";
    expected.remoteEid = "4";
    expected.remoteJettyId = "4";
    EXPECT_NE(sessions.find(expected), sessions.end());
    // 重复 bind 同一会话：覆盖更新，不新增
    ASSERT_EQ(topo.ParseUMQLog(path, sessions), urma::URMA_SUCCESS);
}

TEST(URMATopologyParseUMQLog, RebindOverwritesSession)
{
    TempDir dir;
    // 同一四元组重复 bind：map 键相同，后一次的整行内容覆盖前一次
    std::string first = "2024-01-15 10:30:00 " + BindLine("1", "1", "2", "2");
    std::string second = "2024-01-15 11:30:00 " + BindLine("1", "1", "2", "2");
    std::string path = dir.Write("umq.log", first + "\n" + second + "\n");
    urma::topo::URMATopology topo;
    std::map<urma::topo::SessionKey, std::string> sessions;
    ASSERT_EQ(topo.ParseUMQLog(path, sessions), urma::URMA_SUCCESS);
    ASSERT_EQ(sessions.size(), 1u);
    EXPECT_EQ(sessions.begin()->second, second);

    // remote jetty_id 不同即为不同四元组：各自独立成会话
    std::string path2 = dir.Write("umq2.log", BindLine("1", "1", "2", "2") + "\n" +
                                            BindLine("1", "1", "2", "9") + "\n");
    std::map<urma::topo::SessionKey, std::string> sessions2;
    ASSERT_EQ(topo.ParseUMQLog(path2, sessions2), urma::URMA_SUCCESS);
    EXPECT_EQ(sessions2.size(), 2u);
}

TEST(URMATopologyParseUMQLog, DirectoryCollectsOnlyLogFiles)
{
    TempDir dir;
    dir.Write("a.log", BindLine("1", "1", "2", "2") + "\n");
    dir.Write("b.log", BindLine("3", "3", "4", "4") + "\n");
    dir.Write("c.txt", BindLine("5", "5", "6", "6") + "\n"); // 非 .log 不收集

    urma::topo::URMATopology topo;
    std::map<urma::topo::SessionKey, std::string> sessions;
    ASSERT_EQ(topo.ParseUMQLog(dir.Path().string(), sessions), urma::URMA_SUCCESS);
    EXPECT_EQ(sessions.size(), 2u);
}

TEST(URMATopologyParseUMQLog, DirectoryWithoutLogFilesSucceeds)
{
    TempDir dir;
    dir.Write("notes.txt", "hello\n");
    urma::topo::URMATopology topo;
    std::map<urma::topo::SessionKey, std::string> sessions;
    // 目录存在但没有 .log 文件：视为成功，会话为空
    EXPECT_EQ(topo.ParseUMQLog(dir.Path().string(), sessions), urma::URMA_SUCCESS);
    EXPECT_TRUE(sessions.empty());
}

TEST(URMATopologyParseUMQLog, MalformedBindLineFails)
{
    TempDir dir;
    // 命中 bind jetty success 但无法解析出四元组
    std::string path = dir.Write("bad.log", "umq: bind jetty success, but no session fields\n");
    urma::topo::URMATopology topo;
    std::map<urma::topo::SessionKey, std::string> sessions;
    EXPECT_EQ(topo.ParseUMQLog(path, sessions), urma::URMA_FAIL);
}

TEST(URMATopologyParseUMQLog, UnreadableFileFails)
{
    TempDir dir;
    std::string path = dir.Write("locked.log", BindLine("1", "1", "2", "2") + "\n");
    ASSERT_EQ(::chmod(path.c_str(), 0000), 0);
    urma::topo::URMATopology topo;
    std::map<urma::topo::SessionKey, std::string> sessions;
    EXPECT_EQ(topo.ParseUMQLog(path, sessions), urma::URMA_FAIL);
    ::chmod(path.c_str(), 0644); // 恢复权限便于临时目录清理
}

// ---------------------------------------------------------------------------
// CreateTopology：模式分发与参数校验
// ---------------------------------------------------------------------------

TEST(URMATopologyCreateTopology, UnknownPodModeFails)
{
    urma::topo::URMATopology topo;
    auto args = MakeArgs("bogus", {});
    EXPECT_EQ(topo.CreateTopology(args), urma::URMA_FAIL);
}

TEST(URMATopologyCreateTopology, NormalModeWithoutNormalEntryFails)
{
    // podMode=off 但 umq_log_path_map 中没有 "normal" 键
    urma::topo::URMATopology topo;
    auto args = MakeArgs("off", {{"pod1", "/tmp/whatever.log"}});
    EXPECT_EQ(topo.CreateTopology(args), urma::URMA_FAIL);
}

TEST(URMATopologyCreateTopology, PodModeWithUnknownPodIdFails)
{
    // pod_id_list 中的 pod 不在 umq_log_path_map 中
    urma::topo::URMATopology topo;
    auto args = MakeArgs("on", {{"pod1", "/tmp/a.log"}}, {"pod_ghost"});
    EXPECT_EQ(topo.CreateTopology(args), urma::URMA_FAIL);
}

TEST(URMATopologyCreateTopology, PodModeBadLogFails)
{
    TempDir dir;
    std::string path = dir.Write("bad.log", "umq: bind jetty success, but no session fields\n");
    urma::topo::URMATopology topo;
    auto args = MakeArgs("on", {{"pod1", path}});
    EXPECT_EQ(topo.CreateTopology(args), urma::URMA_FAIL);
}

TEST(URMATopologyCreateTopology, NormalModeBadLogFails)
{
    TempDir dir;
    std::string path = dir.Write("bad.log", "umq: bind jetty success, but no session fields\n");
    urma::topo::URMATopology topo;
    auto args = MakeArgs("off", {{"normal", path}});
    EXPECT_EQ(topo.CreateTopology(args), urma::URMA_FAIL);
}

TEST(URMATopologyCreateTopology, PodModeSubsetOfPodIdList)
{
    // pod_id_list 指定 pod1：pod2 的缺失路径不应被处理（否则会 FAIL）
    TempDir dir;
    std::string path = dir.Write("good.log", BindLine("1", "1", "2", "2") + "\n");
    urma::topo::URMATopology topo;
    auto args = MakeArgs("on", {{"pod1", path}, {"pod2", "/nonexistent/pod2.log"}}, {"pod1"});
    // 注意：pod 模式下 JSON 输出目录 /var/witty-ub 不可写时写文件失败，
    // 但实现选择吞掉该失败并返回 SUCCESS（已在报告中记录为问题）
    EXPECT_EQ(topo.CreateTopology(args), urma::URMA_SUCCESS);
}

TEST(URMATopologyCreateTopology, PodModeFullFlowReachesFileWrite)
{
    // 空 pod_id_list 处理 map 中全部 pod；写 /var/witty-ub/urma-topology.json 失败被吞掉
    TempDir dir;
    std::string path = dir.Write("good.log", BindLine("1", "1", "2", "2") + "\n");
    urma::topo::URMATopology topo;
    auto args = MakeArgs("on", {{"pod1", path}});
    EXPECT_EQ(topo.CreateTopology(args), urma::URMA_SUCCESS);
}

TEST(URMATopologyCreateTopology, NormalModeFailsWhenOutputNotWritable)
{
    // 正常模式：解析成功但 /var/witty-ub 不可写时返回 FAIL（与 pod 模式行为不一致）
    TempDir dir;
    std::string path = dir.Write("good.log", BindLine("1", "1", "2", "2") + "\n");
    urma::topo::URMATopology topo;
    auto args = MakeArgs("off", {{"normal", path}});
    EXPECT_EQ(topo.CreateTopology(args), urma::URMA_FAIL);
}
