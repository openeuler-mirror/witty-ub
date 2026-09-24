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

#include <unistd.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>
#include <unordered_map>
#include <vector>

#include "failure_def.h"
#include "logger.h"
#include "rack_error.h"

// 访问 LogCollector / UbseContext 私有成员
// 注意：必须带目录包含，避免解析到 brpc_diag_tool 下的同名 log_collector.h
#define private public
#include "log/log_collector.h"
#include "ubse_context.h"
#undef private

namespace failure::log {
// log_collector.cpp 中定义但未在头文件声明的自由函数
bool IsResourceScopedComponent(const std::string &component);
bool MatchProgramProc(const FailureEvent &event, const FailureMetadata &meta);
void CacheUmqEndpointFields(FailureEvent &event);
bool MatchUmqEndpoints(FailureEvent &event, const FailureMetadata &meta);
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
               ("witty_collector_test_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) +
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

// 临时切换工作目录（用于 ./data/failure_mode.json 回退路径），析构时还原
class ScopedChdir {
public:
    explicit ScopedChdir(const std::filesystem::path &p) : old_(std::filesystem::current_path()) { ::chdir(p.c_str()); }
    ~ScopedChdir() { ::chdir(old_.c_str()); }

private:
    std::filesystem::path old_;
};

// 直接覆盖 UbseContext 单例参数表
void SetArgMap(std::unordered_map<std::string, std::string> m)
{
    ubse::context::UbseContext::GetInstance().argMap = std::move(m);
}

constexpr int64_t T0 = 1700000000000000LL;                       // 固定基准时间（过去）
constexpr int64_t TEN_SECONDS_US = 10 * 1000 * 1000LL;           // 时间窗口
const std::string EID1 = "0000:0000:0000:0000:0000:0000:0000:0011";
const std::string EID2 = "0000:0000:0000:0000:0000:0000:0000:0022";

// 构造一条 umq 关键函数事件（alarm_level=error）
failure::FailureEvent MakeUmqEvent(int64_t ts, std::string funcName, std::string program = "umq_proc")
{
    failure::FailureEvent ev{};
    ev.timestamp = ts;
    ev.component = "umq";
    ev.text = "umq log line at " + std::to_string(ts);
    ev.attributes["alarm_level"] = "error";
    ev.attributes["function_name"] = std::move(funcName);
    ev.attributes["program_name"] = std::move(program);
    ev.attributes["proc_id"] = "123";
    ev.attributes["thread_id"] = "77";
    return ev;
}

// 构造一个带双端端点内容的 umq 事件
failure::FailureEvent MakeBiEndpointUmqEvent(int64_t ts)
{
    auto ev = MakeUmqEvent(ts, "umq_ub_post_tx");
    ev.attributes["content"] = "local eid: " + EID1 + ", local jetty_id: 7, remote eid: " + EID2 +
                               ", remote jetty_id: 9";
    return ev;
}

// 构造非 umq 组件事件（带时间戳与可选 pod）
failure::FailureEvent MakeEvent(const std::string &component, int64_t ts,
                                std::optional<std::string> podId = std::nullopt)
{
    failure::FailureEvent ev{};
    ev.timestamp = ts;
    ev.component = component;
    ev.text = component + " log line";
    ev.pathCell.podId = std::move(podId);
    ev.pathCell.path = "/var/log/" + component;
    return ev;
}
} // namespace

// ---------- 自由函数：组件/匹配 ----------

TEST(CollectorHelpers, ResourceScopedComponents)
{
    // 资源域组件四类
    EXPECT_TRUE(failure::log::IsResourceScopedComponent("urmacore"));
    EXPECT_TRUE(failure::log::IsResourceScopedComponent("udmacore"));
    EXPECT_TRUE(failure::log::IsResourceScopedComponent("libudma"));
    EXPECT_TRUE(failure::log::IsResourceScopedComponent("ubsocket"));
    // 其余组件不属于资源域
    EXPECT_FALSE(failure::log::IsResourceScopedComponent("umq"));
    EXPECT_FALSE(failure::log::IsResourceScopedComponent("liburma"));
    EXPECT_FALSE(failure::log::IsResourceScopedComponent("hardware"));
    EXPECT_FALSE(failure::log::IsResourceScopedComponent(""));
}

TEST(CollectorHelpers, MatchProgramProcRequiresBothAttributes)
{
    failure::FailureMetadata meta;
    meta.programName = "umq_proc";
    meta.procId = "123";

    failure::FailureEvent ev{};
    ev.attributes["program_name"] = "umq_proc";
    ev.attributes["proc_id"] = "123";
    EXPECT_TRUE(failure::log::MatchProgramProc(ev, meta));

    // 程序名不匹配
    ev.attributes["program_name"] = "other";
    EXPECT_FALSE(failure::log::MatchProgramProc(ev, meta));
    // proc_id 不匹配
    ev.attributes["program_name"] = "umq_proc";
    ev.attributes["proc_id"] = "9";
    EXPECT_FALSE(failure::log::MatchProgramProc(ev, meta));
    // 缺属性
    failure::FailureEvent evNoAttrs{};
    EXPECT_FALSE(failure::log::MatchProgramProc(evNoAttrs, meta));
    // 只有一半属性
    failure::FailureEvent evHalf{};
    evHalf.attributes["program_name"] = "umq_proc";
    EXPECT_FALSE(failure::log::MatchProgramProc(evHalf, meta));
}

TEST(CollectorHelpers, CacheUmqEndpointFieldsFromContent)
{
    // 双端内容：提取 local/remote 四个字段
    failure::FailureEvent bi = MakeBiEndpointUmqEvent(T0);
    failure::log::CacheUmqEndpointFields(bi);
    EXPECT_EQ(bi.attributes.at("local_eid"), EID1);
    EXPECT_EQ(bi.attributes.at("local_jetty_id"), "7");
    EXPECT_EQ(bi.attributes.at("remote_eid"), EID2);
    EXPECT_EQ(bi.attributes.at("remote_jetty_id"), "9");

    // 单端内容：仅提取 local 两个字段
    failure::FailureEvent single = MakeUmqEvent(T0, "umq_ub_post_tx");
    single.attributes["content"] = "prefix eid: " + EID2 + ", jetty_id: 5, suffix";
    failure::log::CacheUmqEndpointFields(single);
    EXPECT_EQ(single.attributes.at("local_eid"), EID2);
    EXPECT_EQ(single.attributes.at("local_jetty_id"), "5");
    EXPECT_EQ(single.attributes.count("remote_eid"), 0u);
    EXPECT_EQ(single.attributes.count("remote_jetty_id"), 0u);

    // 已缓存 local 两字段：直接返回，不再解析
    failure::FailureEvent cached = MakeUmqEvent(T0, "umq_ub_post_tx");
    cached.attributes["local_eid"] = "already";
    cached.attributes["local_jetty_id"] = "1";
    cached.attributes["content"] = "local eid: " + EID1 + ", local jetty_id: 7, remote eid: " + EID2 +
                                   ", remote jetty_id: 9";
    failure::log::CacheUmqEndpointFields(cached);
    EXPECT_EQ(cached.attributes.at("local_eid"), "already");
    EXPECT_EQ(cached.attributes.count("remote_eid"), 0u);

    // 只有 local_eid（不齐两个字段）仍会尝试解析 content
    failure::FailureEvent half = MakeUmqEvent(T0, "umq_ub_post_tx");
    half.attributes["local_eid"] = "x";
    half.attributes["content"] = "eid: " + EID2 + ", jetty_id: 5";
    failure::log::CacheUmqEndpointFields(half);
    EXPECT_EQ(half.attributes.at("local_eid"), EID2); // 被解析结果覆盖

    // 无 content 属性：直接返回
    failure::FailureEvent noContent = MakeUmqEvent(T0, "umq_ub_post_tx");
    failure::log::CacheUmqEndpointFields(noContent);
    EXPECT_EQ(noContent.attributes.count("local_eid"), 0u);

    // content 不匹配任何模式：不写字段
    failure::FailureEvent noMatch = MakeUmqEvent(T0, "umq_ub_post_tx");
    noMatch.attributes["content"] = "plain text without endpoints";
    failure::log::CacheUmqEndpointFields(noMatch);
    EXPECT_EQ(noMatch.attributes.count("local_eid"), 0u);
}

TEST(CollectorHelpers, MatchUmqEndpointsAllFields)
{
    failure::FailureMetadata meta;
    meta.localEid = EID1;
    meta.localJettyId = "7";

    // 本地两端匹配且双方都无远端 -> nullopt == nullopt
    failure::FailureEvent ev{};
    ev.attributes["local_eid"] = EID1;
    ev.attributes["local_jetty_id"] = "7";
    EXPECT_TRUE(failure::log::MatchUmqEndpoints(ev, meta));

    // 本地 eid 不匹配
    ev.attributes["local_eid"] = EID2;
    EXPECT_FALSE(failure::log::MatchUmqEndpoints(ev, meta));

    // 事件带远端而元数据没有 -> 不匹配
    ev.attributes["local_eid"] = EID1;
    ev.attributes["remote_eid"] = EID2;
    EXPECT_FALSE(failure::log::MatchUmqEndpoints(ev, meta));

    // 元数据带远端而事件没有 -> 不匹配
    failure::FailureEvent ev2{};
    ev2.attributes["local_eid"] = EID1;
    ev2.attributes["local_jetty_id"] = "7";
    meta.remoteEid = EID2;
    EXPECT_FALSE(failure::log::MatchUmqEndpoints(ev2, meta));

    // 远端 eid 一致但 jetty 不一致 -> 不匹配
    ev2.attributes["remote_eid"] = EID2;
    ev2.attributes["remote_jetty_id"] = "3";
    meta.remoteJettyId = "9";
    EXPECT_FALSE(failure::log::MatchUmqEndpoints(ev2, meta));

    // 四端全匹配
    ev2.attributes["remote_jetty_id"] = "9";
    EXPECT_TRUE(failure::log::MatchUmqEndpoints(ev2, meta));

    // 事件缺本地字段 -> 不匹配
    failure::FailureEvent ev3{};
    EXPECT_FALSE(failure::log::MatchUmqEndpoints(ev3, meta));
}

// ---------- 参数校验 ----------

TEST(CollectorValidation, PodIdRules)
{
    failure::log::LogCollector collector;
    // 合法：小写字母数字，中间连字符
    EXPECT_TRUE(collector.IsValidPodId("abc123"));
    EXPECT_TRUE(collector.IsValidPodId("a-b-c"));
    // 非法：空、过长（>253）、大写、下划线、首尾连字符
    EXPECT_FALSE(collector.IsValidPodId(""));
    EXPECT_FALSE(collector.IsValidPodId(std::string(254, 'a')));
    EXPECT_TRUE(collector.IsValidPodId(std::string(253, 'a')));
    EXPECT_FALSE(collector.IsValidPodId("Abc"));
    EXPECT_FALSE(collector.IsValidPodId("a_b"));
    EXPECT_FALSE(collector.IsValidPodId("-abc"));
    EXPECT_FALSE(collector.IsValidPodId("abc-"));
    // 单字符 '-' 同时是首尾 -> 非法
    EXPECT_FALSE(collector.IsValidPodId("-"));
}

TEST(CollectorValidation, PathRules)
{
    failure::log::LogCollector collector;
    TempDir dir;
    auto existing = (dir.Path() / "exist.log").string();
    WriteFile(existing, "x");
    // 合法：存在的绝对路径
    EXPECT_TRUE(collector.IsValidPath(existing));
    // 非法：空、相对路径、不存在
    EXPECT_FALSE(collector.IsValidPath(""));
    EXPECT_FALSE(collector.IsValidPath("relative/path"));
    EXPECT_FALSE(collector.IsValidPath("/definitely/not/exist/path"));
}

TEST(CollectorValidation, EidRules)
{
    failure::log::LogCollector collector;
    // 合法：8 段 4 位十六进制
    EXPECT_TRUE(collector.IsValidEid(EID1));
    // 非法：空、非法字符 g、段数不足、段长度不对
    EXPECT_FALSE(collector.IsValidEid(""));
    EXPECT_FALSE(collector.IsValidEid("gggg:0000:0000:0000:0000:0000:0000:0000"));
    EXPECT_FALSE(collector.IsValidEid("0000:0000:0000"));
    EXPECT_FALSE(collector.IsValidEid("000:0000:0000:0000:0000:0000:0000:0000"));
    // 7 段 -> 段数不符
    EXPECT_FALSE(collector.IsValidEid("0000:0000:0000:0000:0000:0000:0000"));
}

TEST(CollectorValidation, JettyIdRules)
{
    failure::log::LogCollector collector;
    EXPECT_TRUE(collector.IsValidJettyId("123"));
    EXPECT_TRUE(collector.IsValidJettyId("0"));
    EXPECT_FALSE(collector.IsValidJettyId(""));
    EXPECT_FALSE(collector.IsValidJettyId("12a"));
    EXPECT_FALSE(collector.IsValidJettyId("12.3"));
    // 纯数字但超出 int 范围 -> stoi 抛异常被捕获
    EXPECT_FALSE(collector.IsValidJettyId("99999999999"));
}

// ---------- 参数解析 ----------

TEST(CollectorParse, PodMode)
{
    failure::log::LogCollector collector;
    // 缺失
    SetArgMap({});
    EXPECT_EQ(collector.ParsePodMode(ubse::context::UbseContext::GetInstance().argMap), RACK_FAIL);
    // 非法值
    SetArgMap({{"pod-mode", "maybe"}});
    EXPECT_EQ(collector.ParsePodMode(ubse::context::UbseContext::GetInstance().argMap), RACK_FAIL);
    // on / off
    SetArgMap({{"pod-mode", "on"}});
    EXPECT_EQ(collector.ParsePodMode(ubse::context::UbseContext::GetInstance().argMap), RACK_OK);
    EXPECT_TRUE(collector.podMode_);
    SetArgMap({{"pod-mode", "off"}});
    EXPECT_EQ(collector.ParsePodMode(ubse::context::UbseContext::GetInstance().argMap), RACK_OK);
    EXPECT_FALSE(collector.podMode_);
}

TEST(CollectorParse, TimeRange)
{
    failure::log::LogCollector collector;
    const auto &argMap = ubse::context::UbseContext::GetInstance().argMap;
    // 缺 start-time
    SetArgMap({{"end-time", "2024-06-01 09:00:00"}});
    EXPECT_EQ(collector.ParseTimeRange(argMap), RACK_FAIL);
    // start-time 非法
    SetArgMap({{"start-time", "garbage"}, {"end-time", "2024-06-01 09:00:00"}});
    EXPECT_EQ(collector.ParseTimeRange(argMap), RACK_FAIL);
    // 缺 end-time
    SetArgMap({{"start-time", "2024-06-01 08:00:00"}});
    EXPECT_EQ(collector.ParseTimeRange(argMap), RACK_FAIL);
    // end-time 非法
    SetArgMap({{"start-time", "2024-06-01 08:00:00"}, {"end-time", "bad"}});
    EXPECT_EQ(collector.ParseTimeRange(argMap), RACK_FAIL);
    // start 晚于 end
    SetArgMap({{"start-time", "2024-06-02 08:00:00"}, {"end-time", "2024-06-01 08:00:00"}});
    EXPECT_EQ(collector.ParseTimeRange(argMap), RACK_FAIL);
    // 合法：endTime 补齐 999999 微秒
    SetArgMap({{"start-time", "2024-06-01 08:00:00"}, {"end-time", "2024-06-01 09:00:00"}});
    EXPECT_EQ(collector.ParseTimeRange(argMap), RACK_OK);
    auto expectedStart = failure::DatetimeStrToTimestamp("2024-06-01 08:00:00").value();
    auto expectedEnd = failure::DatetimeStrToTimestamp("2024-06-01 09:00:00").value();
    EXPECT_EQ(collector.query_.startTime, expectedStart);
    EXPECT_EQ(collector.query_.endTime, expectedEnd + 999999LL);
}

TEST(CollectorParse, EventTypes)
{
    failure::log::LogCollector collector;
    const auto &argMap = ubse::context::UbseContext::GetInstance().argMap;
    // 缺省：不过滤
    SetArgMap({});
    EXPECT_EQ(collector.ParseEventTypes(argMap), RACK_OK);
    EXPECT_TRUE(collector.query_.eventTypes.empty());
    // 空串
    SetArgMap({{"event-type", ""}});
    EXPECT_EQ(collector.ParseEventTypes(argMap), RACK_FAIL);
    // 非法值
    SetArgMap({{"event-type", "foo"}});
    EXPECT_EQ(collector.ParseEventTypes(argMap), RACK_FAIL);
    // 合法（重复值去重）
    SetArgMap({{"event-type", "bind,post,bind"}});
    EXPECT_EQ(collector.ParseEventTypes(argMap), RACK_OK);
    EXPECT_EQ(collector.query_.eventTypes.size(), 2u);
    EXPECT_NE(collector.query_.eventTypes.find(failure::EventTypeOption::BIND), collector.query_.eventTypes.end());
    EXPECT_NE(collector.query_.eventTypes.find(failure::EventTypeOption::POST), collector.query_.eventTypes.end());
}

TEST(CollectorParse, PodIds)
{
    const auto &argMap = ubse::context::UbseContext::GetInstance().argMap;
    // 缺省：不解析
    SetArgMap({});
    {
        failure::log::LogCollector collector;
        EXPECT_EQ(collector.ParsePodIds(argMap), RACK_OK);
        EXPECT_TRUE(collector.query_.podIds.empty());
    }
    // 非 pod 模式出现 pod-id：报错
    SetArgMap({{"pod-id", "pod-1"}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = false;
        EXPECT_EQ(collector.ParsePodIds(argMap), RACK_FAIL);
    }
    // 空值
    SetArgMap({{"pod-id", ""}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        EXPECT_EQ(collector.ParsePodIds(argMap), RACK_FAIL);
    }
    SetArgMap({{"pod-id", "pod-1"}});
    // 非法 pod id
    SetArgMap({{"pod-id", "Pod1"}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        EXPECT_EQ(collector.ParsePodIds(argMap), RACK_FAIL);
    }
    // pod id 不在任何组件的日志路径中
    SetArgMap({{"pod-id", "pod-1"}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        collector.allowedPodIds_["umq"] = {"pod-2"};
        EXPECT_EQ(collector.ParsePodIds(argMap), RACK_FAIL);
    }
    // 部分组件未提供该 pod id
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        collector.allowedPodIds_["umq"] = {"pod-1"};
        collector.allowedPodIds_["ubsocket"] = {"pod-2"};
        EXPECT_EQ(collector.ParsePodIds(argMap), RACK_FAIL);
    }
    // 合法：所有组件都提供
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        collector.allowedPodIds_["umq"] = {"pod-1"};
        collector.allowedPodIds_["ubsocket"] = {"pod-1", "pod-2"};
        EXPECT_EQ(collector.ParsePodIds(argMap), RACK_OK);
        EXPECT_EQ(collector.query_.podIds.size(), 1u);
    }
    // 重复 pod id
    SetArgMap({{"pod-id", "pod-1,pod-1"}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        collector.allowedPodIds_["umq"] = {"pod-1"};
        EXPECT_EQ(collector.ParsePodIds(argMap), RACK_FAIL);
    }
}

TEST(CollectorParse, LocalEidsAndJettyIds)
{
    const auto &argMap = ubse::context::UbseContext::GetInstance().argMap;
    // local-eid 缺省
    SetArgMap({});
    {
        failure::log::LogCollector collector;
        EXPECT_EQ(collector.ParseLocalEids(argMap), RACK_OK);
        EXPECT_EQ(collector.ParseJettyIds(argMap), RACK_OK);
        EXPECT_TRUE(collector.query_.localEids.empty());
        EXPECT_TRUE(collector.query_.jettyIds.empty());
    }
    // 非法 local-eid
    SetArgMap({{"local-eid", "nothex"}});
    {
        failure::log::LogCollector collector;
        EXPECT_EQ(collector.ParseLocalEids(argMap), RACK_FAIL);
    }
    // 合法 local-eid（重复 -> 失败）
    SetArgMap({{"local-eid", EID1 + "," + EID2}});
    {
        failure::log::LogCollector collector;
        EXPECT_EQ(collector.ParseLocalEids(argMap), RACK_OK);
        EXPECT_EQ(collector.query_.localEids.size(), 2u);
    }
    SetArgMap({{"local-eid", EID1 + "," + EID1}});
    {
        failure::log::LogCollector collector;
        EXPECT_EQ(collector.ParseLocalEids(argMap), RACK_FAIL);
    }
    // jetty-id 非法
    SetArgMap({{"jetty-id", "12a"}});
    {
        failure::log::LogCollector collector;
        EXPECT_EQ(collector.ParseJettyIds(argMap), RACK_FAIL);
    }
    // jetty-id 超长
    SetArgMap({{"jetty-id", "99999999999"}});
    {
        failure::log::LogCollector collector;
        EXPECT_EQ(collector.ParseJettyIds(argMap), RACK_FAIL);
    }
    // jetty-id 合法
    SetArgMap({{"jetty-id", "1,2"}});
    {
        failure::log::LogCollector collector;
        EXPECT_EQ(collector.ParseJettyIds(argMap), RACK_OK);
        EXPECT_EQ(collector.query_.jettyIds.size(), 2u);
    }
    // jetty-id 重复
    SetArgMap({{"jetty-id", "1,1"}});
    {
        failure::log::LogCollector collector;
        EXPECT_EQ(collector.ParseJettyIds(argMap), RACK_FAIL);
    }
}

TEST(CollectorParse, LogPathPodModeOff)
{
    const auto &argMap = ubse::context::UbseContext::GetInstance().argMap;
    TempDir dir;
    auto logFile = (dir.Path() / "umq.log").string();
    WriteFile(logFile, "x");

    // 全部缺省：允许
    SetArgMap({});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = false;
        EXPECT_EQ(collector.ParseLogPath(argMap), RACK_OK);
        EXPECT_TRUE(collector.customizedLogPath_.empty());
    }
    // 提供存在的绝对路径：按单路径处理
    SetArgMap({{"umq-log-path", logFile}, {"urmacore-log-path", logFile}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = false;
        EXPECT_EQ(collector.ParseLogPath(argMap), RACK_OK);
        EXPECT_EQ(collector.customizedLogPath_.size(), 2u);
        ASSERT_EQ(collector.customizedLogPath_["umq"].size(), 1u);
        EXPECT_FALSE(collector.customizedLogPath_["umq"][0].podId.has_value());
        EXPECT_EQ(collector.customizedLogPath_["umq"][0].path, logFile);
    }
    // 相对路径 / 不存在路径：失败
    SetArgMap({{"umq-log-path", "relative/path"}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = false;
        EXPECT_EQ(collector.ParseLogPath(argMap), RACK_FAIL);
    }
    SetArgMap({{"umq-log-path", "/definitely/not/exist"}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = false;
        EXPECT_EQ(collector.ParseLogPath(argMap), RACK_FAIL);
    }
}

TEST(CollectorParse, LogPathPodModeOn)
{
    const auto &argMap = ubse::context::UbseContext::GetInstance().argMap;
    TempDir dir;
    auto pathA = (dir.Path() / "a.log").string();
    auto pathB = (dir.Path() / "b.log").string();
    WriteFile(pathA, "x");
    WriteFile(pathB, "x");

    // pod 模式下 ubsocket/umq/liburma/libudma 为必填
    SetArgMap({{"pod-mode", "on"}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        EXPECT_EQ(collector.ParseLogPath(argMap), RACK_FAIL);
    }
    // 四个必填组件齐全（urmacore/udmacore 可选）：按 pod:path 拆分
    SetArgMap({{"ubsocket-log-path", "pod-1:" + pathA},
               {"umq-log-path", "pod-1:" + pathB},
               {"liburma-log-path", "pod-1:" + pathA},
               {"libudma-log-path", "pod-1:" + pathB}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        EXPECT_EQ(collector.ParseLogPath(argMap), RACK_OK);
        EXPECT_EQ(collector.customizedLogPath_.size(), 4u);
        ASSERT_EQ(collector.customizedLogPath_["umq"].size(), 1u);
        EXPECT_EQ(collector.customizedLogPath_["umq"][0].podId.value_or(""), "pod-1");
        EXPECT_EQ(collector.customizedLogPath_["umq"][0].path, pathB);
        EXPECT_EQ(collector.allowedPodIds_["umq"].size(), 1u);
    }
    // 可选组件提供单路径（不拆 pod）
    SetArgMap({{"ubsocket-log-path", "pod-1:" + pathA},
               {"umq-log-path", "pod-1:" + pathB},
               {"liburma-log-path", "pod-1:" + pathA},
               {"libudma-log-path", "pod-1:" + pathB},
               {"urmacore-log-path", pathA}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        EXPECT_EQ(collector.ParseLogPath(argMap), RACK_OK);
        ASSERT_EQ(collector.customizedLogPath_["urmacore"].size(), 1u);
        EXPECT_FALSE(collector.customizedLogPath_["urmacore"][0].podId.has_value());
    }
    // 多 pod 逗号分隔 + 重复 pod id：失败
    SetArgMap({{"ubsocket-log-path", "pod-1:" + pathA + ",pod-1:" + pathB}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        EXPECT_EQ(collector.HandleLogPath(argMap, "ubsocket", true, true), RACK_FAIL);
    }
    // 多 pod 合法
    SetArgMap({{"ubsocket-log-path", "pod-1:" + pathA + ",pod-2:" + pathB}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        EXPECT_EQ(collector.HandleLogPath(argMap, "ubsocket", true, true), RACK_OK);
        EXPECT_EQ(collector.customizedLogPath_["ubsocket"].size(), 2u);
    }
    // 空串 / 缺冒号 / 非法 pod / 相对路径
    SetArgMap({{"umq-log-path", ""}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        EXPECT_EQ(collector.HandleLogPath(argMap, "umq", true, true), RACK_FAIL);
    }
    SetArgMap({{"umq-log-path", "no-colon-here"}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        EXPECT_EQ(collector.HandleLogPath(argMap, "umq", true, true), RACK_FAIL);
    }
    SetArgMap({{"umq-log-path", "Pod1:" + pathA}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        EXPECT_EQ(collector.HandleLogPath(argMap, "umq", true, true), RACK_FAIL);
    }
    SetArgMap({{"umq-log-path", "pod-1:relative/path"}});
    {
        failure::log::LogCollector collector;
        collector.podMode_ = true;
        EXPECT_EQ(collector.HandleLogPath(argMap, "umq", true, true), RACK_FAIL);
    }
}

TEST(CollectorParse, ParseArgsFullSuccess)
{
    TempDir dir;
    auto logFile = (dir.Path() / "umq.log").string();
    WriteFile(logFile, "x");
    SetArgMap({{"pod-mode", "off"},
               {"start-time", "2024-06-01 08:00:00"},
               {"end-time", "2024-06-01 09:00:00"},
               {"umq-log-path", logFile},
               {"event-type", "bind"},
               {"local-eid", EID1},
               {"jetty-id", "7"}});
    failure::log::LogCollector collector;
    EXPECT_EQ(collector.ParseArgs(), RACK_OK);
    EXPECT_FALSE(collector.podMode_);
    EXPECT_EQ(collector.query_.eventTypes.size(), 1u);
    EXPECT_EQ(collector.query_.localEids.size(), 1u);
    EXPECT_EQ(collector.query_.jettyIds.size(), 1u);
    EXPECT_EQ(collector.customizedLogPath_.size(), 1u);

    // 缺 pod-mode：整体失败
    SetArgMap({{"start-time", "2024-06-01 08:00:00"}, {"end-time", "2024-06-01 09:00:00"}});
    failure::log::LogCollector bad;
    EXPECT_EQ(bad.ParseArgs(), RACK_FAIL);
}

// ---------- 故障模式文件 ----------

TEST(CollectorFailureModes, OpenFailureModeFileFallbackAndFailure)
{
    failure::log::LogCollector collector;
    TempDir dir;
    // 两个路径都不存在
    {
        ScopedChdir chdir(dir.Path());
        std::ifstream ifs;
        EXPECT_EQ(collector.OpenFailureModeFile(ifs), RACK_FAIL);
    }
    // 工作目录下存在 ./data/failure_mode.json：回退成功
    std::filesystem::create_directories(dir.Path() / "data");
    WriteFile(dir.Path() / "data/failure_mode.json", "[]");
    {
        ScopedChdir chdir(dir.Path());
        std::ifstream ifs;
        EXPECT_EQ(collector.OpenFailureModeFile(ifs), RACK_OK);
        EXPECT_TRUE(ifs.is_open());
        std::string content((std::istreambuf_iterator<char>(ifs)), std::istreambuf_iterator<char>());
        EXPECT_EQ(content, "[]");
    }
}

TEST(CollectorFailureModes, ParseFailureModesAndOverridePaths)
{
    failure::log::LogCollector collector;
    TempDir dir;
    auto modeFile = dir.Path() / "modes.json";
    WriteFile(modeFile, R"([
        {"component":"umq","version":"1.0","is_multiline":false,"manifest":"<a>|<b>","log_path":"/var/log/umdk/umq/"},
        {"component":"hardware","version":"1.0","is_multiline":false,"manifest":"<a>","log_path":"/var/log/message"}
    ])");
    std::ifstream ifs(modeFile);
    ASSERT_TRUE(ifs.is_open());
    std::vector<failure::FailureMode> modes;
    EXPECT_EQ(collector.ParseFailureModes(ifs, modes), RACK_OK);
    ASSERT_EQ(modes.size(), 2u);
    EXPECT_EQ(modes[0].component, "umq");
    EXPECT_EQ(modes[0].dataSource.option, failure::DataSourceOption::USER);
    EXPECT_FALSE(modes[0].isMultiline);
    EXPECT_EQ(modes[1].dataSource.option, failure::DataSourceOption::KERNEL);

    // customizedLogPath_ 覆盖模式自带路径
    std::ifstream ifs2(modeFile);
    failure::log::LogCollector collector2;
    collector2.customizedLogPath_["umq"] = {failure::PathCell{"pod-9", "/tmp/custom.log"}};
    EXPECT_EQ(collector2.ParseFailureModes(ifs2, modes), RACK_OK);
    ASSERT_EQ(modes.size(), 2u);
    ASSERT_EQ(modes[0].dataSource.pathCells.size(), 1u);
    EXPECT_EQ(modes[0].dataSource.pathCells[0].podId.value_or(""), "pod-9");
    EXPECT_EQ(modes[0].dataSource.pathCells[0].path, "/tmp/custom.log");
    // hardware 未覆盖，保留原路径
    EXPECT_EQ(modes[1].dataSource.pathCells[0].path, "/var/log/message");

    // 非法 JSON：失败
    auto badFile = dir.Path() / "bad.json";
    WriteFile(badFile, "{invalid");
    std::ifstream ifs3(badFile);
    failure::log::LogCollector collector3;
    EXPECT_EQ(collector3.ParseFailureModes(ifs3, modes), RACK_FAIL);
}

TEST(CollectorFailureModes, ExpandPathCells)
{
    failure::log::LogCollector collector;
    TempDir dir;
    auto fileA = dir.Path() / "a.log";
    WriteFile(fileA, "x");
    // KERNEL：原样返回
    failure::FailureMode kernel;
    kernel.dataSource.option = failure::DataSourceOption::KERNEL;
    failure::PathCell cell{std::nullopt, fileA.string()};
    auto cells = collector.ExpandPathCells(kernel, cell);
    ASSERT_EQ(cells.size(), 1u);
    EXPECT_EQ(cells[0].path, fileA.string());

    // USER + 普通文件：单个 cell
    failure::FailureMode user;
    user.dataSource.option = failure::DataSourceOption::USER;
    cells = collector.ExpandPathCells(user, cell);
    ASSERT_EQ(cells.size(), 1u);
    EXPECT_EQ(cells[0].path, fileA.string());

    // USER + 不存在路径：空
    cells = collector.ExpandPathCells(user, failure::PathCell{std::nullopt, "/definitely/not/exist"});
    EXPECT_TRUE(cells.empty());

    // USER + 目录：展开其中 .log 文件，忽略其他后缀
    auto logDir = dir.Path() / "logs";
    std::filesystem::create_directories(logDir);
    WriteFile(logDir / "one.log", "x");
    WriteFile(logDir / "two.log", "x");
    WriteFile(logDir / "skip.txt", "x");
    cells = collector.ExpandPathCells(user, failure::PathCell{"pod-1", logDir.string()});
    ASSERT_EQ(cells.size(), 2u);
    EXPECT_EQ(cells[0].podId.value_or(""), "pod-1");
    for (const auto &c : cells) {
        EXPECT_EQ(std::filesystem::path(c.path).extension(), ".log");
    }
}

TEST(CollectorFailureModes, CreateReaders)
{
    failure::log::LogCollector collector;
    TempDir dir;
    // 无任何故障模式文件：失败
    {
        ScopedChdir chdir(dir.Path());
        EXPECT_EQ(collector.CreateReaders(), RACK_FAIL);
        EXPECT_TRUE(collector.readers_.empty());
    }

    // 在工作目录准备 ./data/failure_mode.json：
    // umq 与 liburma 指向同一文件（USER 去重为一个 reader），hardware 走 KERNEL 单独一个
    auto sharedLog = dir.Path() / "shared.log";
    auto kernLog = dir.Path() / "kern.log";
    WriteFile(sharedLog, "x");
    WriteFile(kernLog, "x");
    std::filesystem::create_directories(dir.Path() / "data");
    WriteFile(dir.Path() / "data/failure_mode.json",
              R"([{"component":"umq","version":"1","is_multiline":false,"manifest":"<a>","log_path":")" + sharedLog.string() +
                  R"("},{"component":"liburma","version":"1","is_multiline":false,"manifest":"<b>","log_path":")" +
                  sharedLog.string() + R"("},{"component":"hardware","version":"1","is_multiline":false,"manifest":"<c>","log_path":")" +
                  kernLog.string() + R"("}])");
    {
        ScopedChdir chdir(dir.Path());
        failure::log::LogCollector collector2;
        EXPECT_EQ(collector2.CreateReaders(), RACK_OK);
        // 同一路径的两个 USER 模式复用一个 reader，hardware 独立
        EXPECT_EQ(collector2.readers_.size(), 2u);
    }

    // pod 模式路径覆盖后按 podId 区分 reader
    {
        ScopedChdir chdir(dir.Path());
        failure::log::LogCollector collector3;
        collector3.customizedLogPath_["umq"] = {failure::PathCell{"pod-1", sharedLog.string()}};
        collector3.customizedLogPath_["liburma"] = {failure::PathCell{"pod-2", sharedLog.string()}};
        EXPECT_EQ(collector3.CreateReaders(), RACK_OK);
        // pod-1/shared 与 pod-2/shared 键不同 -> 两个 reader，加上 hardware 一个
        EXPECT_EQ(collector3.readers_.size(), 3u);
    }
}

TEST(CollectorBuildGraph, FailsWhenCallstackMissing)
{
    failure::log::LogCollector collector;
    // /var/witty-ub/callstack-analysis/overall_callstack.json 不可达 -> 失败
    EXPECT_EQ(collector.BuildGraph(), RACK_FAIL);
}

// ---------- 元数据收集与关联 ----------

TEST(CollectorMetadata, CollectMetadataFiltersAndMaps)
{
    failure::log::LogCollector collector;
    collector.keyFuncEventTypeMap_ = &failure::keyFuncEventTypeMap;
    collector.keyFuncRoleMap_ = &failure::keyFuncRoleMap;

    failure::FailureEvent evWarn = MakeUmqEvent(T0, "umq_ub_post_tx");
    evWarn.attributes["alarm_level"] = "warn"; // 非error被跳过
    failure::FailureEvent evUnknownFunc = MakeUmqEvent(T0, "not_a_key_func");
    failure::FailureEvent evPost = MakeBiEndpointUmqEvent(T0);
    failure::FailureEvent evBind = MakeUmqEvent(T0 + 1000, "umq_ub_bind_inner_impl"); // 无端点内容

    std::unordered_map<std::string, std::vector<failure::FailureEvent>> eventsMap;
    eventsMap["umq"] = {evWarn, evUnknownFunc, evPost, evBind};

    std::vector<failure::FailureMetadata> metadata;
    collector.CollectMetadata(eventsMap, metadata);
    ASSERT_EQ(metadata.size(), 2u);

    // 字段映射：post 事件带角色与端点
    const failure::FailureMetadata &post = metadata[0];
    EXPECT_EQ(post.eventType, failure::EventTypeOption::POST);
    EXPECT_EQ(post.role.value_or(""), "tx");
    EXPECT_EQ(post.funcName, "umq_ub_post_tx");
    EXPECT_EQ(post.programName, "umq_proc");
    EXPECT_EQ(post.procId, "123");
    EXPECT_EQ(post.threadId, "77");
    EXPECT_EQ(post.timestamp, T0);
    EXPECT_EQ(post.localEid, EID1);
    EXPECT_EQ(post.localJettyId, "7");
    EXPECT_EQ(post.remoteEid.value_or(""), EID2);
    EXPECT_EQ(post.remoteJettyId.value_or(""), "9");

    // bind 事件无角色、无端点
    const failure::FailureMetadata &bind = metadata[1];
    EXPECT_EQ(bind.eventType, failure::EventTypeOption::BIND);
    EXPECT_FALSE(bind.role.has_value());
    EXPECT_TRUE(bind.localEid.empty());
    EXPECT_FALSE(bind.remoteEid.has_value());

    // 查询条件过滤：仅 BIND
    failure::log::LogCollector bindOnly;
    bindOnly.keyFuncEventTypeMap_ = &failure::keyFuncEventTypeMap;
    bindOnly.keyFuncRoleMap_ = &failure::keyFuncRoleMap;
    bindOnly.query_.eventTypes = {failure::EventTypeOption::BIND};
    std::vector<failure::FailureMetadata> filtered;
    bindOnly.CollectMetadata(eventsMap, filtered);
    ASSERT_EQ(filtered.size(), 1u);
    EXPECT_EQ(filtered[0].eventType, failure::EventTypeOption::BIND);

    // 查询条件过滤：local-eid 不匹配
    failure::log::LogCollector eidFilter;
    eidFilter.keyFuncEventTypeMap_ = &failure::keyFuncEventTypeMap;
    eidFilter.keyFuncRoleMap_ = &failure::keyFuncRoleMap;
    eidFilter.query_.localEids = {EID2};
    std::vector<failure::FailureMetadata> filteredByEid;
    eidFilter.CollectMetadata(eventsMap, filteredByEid);
    EXPECT_TRUE(filteredByEid.empty());

    // 查询条件过滤：jetty-id 不匹配
    failure::log::LogCollector jettyFilter;
    jettyFilter.keyFuncEventTypeMap_ = &failure::keyFuncEventTypeMap;
    jettyFilter.keyFuncRoleMap_ = &failure::keyFuncRoleMap;
    jettyFilter.query_.jettyIds = {"999"};
    std::vector<failure::FailureMetadata> filteredByJetty;
    jettyFilter.CollectMetadata(eventsMap, filteredByJetty);
    EXPECT_TRUE(filteredByJetty.empty());
}

TEST(CollectorMetadata, CollectCorrelatedLogsWindowsAndMatching)
{
    failure::log::LogCollector collector;
    failure::FailureMetadata meta;
    meta.timestamp = T0;
    meta.programName = "umq_proc";
    meta.procId = "123";
    meta.localEid = EID1;
    meta.localJettyId = "7";
    meta.podId = "pod-1";

    // umq 相关事件：同进程 / 不同进程 / 端点匹配但不同进程
    failure::FailureEvent umqSame = MakeUmqEvent(T0 - 1, "umq_ub_post_tx");
    failure::FailureEvent umqOther = MakeUmqEvent(T0 - 2, "umq_ub_post_tx", "other_proc");
    failure::FailureEvent umqEndpoint = MakeUmqEvent(T0 - 3, "umq_ub_post_tx", "third_proc");
    umqEndpoint.attributes["local_eid"] = EID1;
    umqEndpoint.attributes["local_jetty_id"] = "7";
    // liburma：仅进程匹配生效
    failure::FailureEvent liburmaMatch = MakeEvent("liburma", T0 - 4);
    liburmaMatch.attributes["program_name"] = "umq_proc";
    liburmaMatch.attributes["proc_id"] = "123";
    failure::FailureEvent liburmaNo = MakeEvent("liburma", T0 - 5);
    // ubsocket：资源域组件，窗口 [T0, T0+10s]
    failure::FailureEvent ubIn = MakeEvent("ubsocket", T0 + 9 * 1000 * 1000LL);
    failure::FailureEvent ubOutEarly = MakeEvent("ubsocket", T0 - 1);
    failure::FailureEvent ubOutLate = MakeEvent("ubsocket", T0 + 11 * 1000 * 1000LL);
    failure::FailureEvent ubExact = MakeEvent("ubsocket", T0);
    // urmacore：窗口 [T0-10s, T0]
    failure::FailureEvent urmaIn = MakeEvent("urmacore", T0 - 9 * 1000 * 1000LL);
    failure::FailureEvent urmaOut = MakeEvent("urmacore", T0 + 1);
    // hardware：跳过
    failure::FailureEvent hw = MakeEvent("hardware", T0);

    // 注意：直接调用 CollectCorrelatedLogs 需自行保证各组件事件按时间升序（CorrelateEvents 会先排序）
    std::unordered_map<std::string, std::vector<failure::FailureEvent>> eventsMap;
    eventsMap["umq"] = {umqEndpoint, umqOther, umqSame};
    eventsMap["liburma"] = {liburmaNo, liburmaMatch};
    eventsMap["ubsocket"] = {ubOutEarly, ubExact, ubIn, ubOutLate};
    eventsMap["urmacore"] = {urmaIn, urmaOut};
    eventsMap["hardware"] = {hw};

    std::vector<failure::FailureMetadata> metadata = {meta};
    collector.CollectCorrelatedLogs(eventsMap, metadata);
    ASSERT_EQ(metadata.size(), 1u);
    // 命中：umqSame(进程) + umqEndpoint(端点) + liburmaMatch(进程) + ubIn/ubExact(窗口) + urmaIn(窗口)
    ASSERT_EQ(metadata[0].events.size(), 6u);
    // 事件按时间戳升序
    int64_t prev = -1;
    for (const auto *ev : metadata[0].events) {
        EXPECT_GE(ev->timestamp, prev);
        prev = ev->timestamp;
    }

    // pod 模式下 pod 不一致的事件被剔除
    failure::log::LogCollector podCollector;
    podCollector.podMode_ = true;
    failure::FailureMetadata podMeta = meta;
    failure::FailureEvent ubPod2 = MakeEvent("ubsocket", T0, "pod-2");
    failure::FailureEvent ubPod1 = MakeEvent("ubsocket", T0, "pod-1");
    failure::FailureEvent ubNoPod = MakeEvent("ubsocket", T0); // 无 pod：不比较
    std::unordered_map<std::string, std::vector<failure::FailureEvent>> podMap;
    podMap["ubsocket"] = {ubPod2, ubPod1, ubNoPod};
    std::vector<failure::FailureMetadata> podMetadata = {podMeta};
    podCollector.CollectCorrelatedLogs(podMap, podMetadata);
    // pod-2 剔除，pod-1 与无 pod 保留
    ASSERT_EQ(podMetadata[0].events.size(), 2u);
}

TEST(CollectorMetadata, FilterFuncNames)
{
    failure::log::LogCollector collector;
    // 空关联表：跳过过滤
    std::vector<failure::FailureMetadata> skip;
    failure::FailureMetadata untouched;
    untouched.funcName = "umq_ub_post_tx";
    skip.push_back(untouched);
    collector.FilterFuncNames(skip);
    EXPECT_TRUE(skip[0].events.empty());

    // 构造关联表：上游 upstream_fn / 下游 downstream_fn
    failure::graph::RelevantFuncs rel;
    rel.upstreamFuncs = {{"upstream_fn", "umq"}};
    rel.upstreamNameIndex["upstream_fn"] = {0};
    rel.downstreamFuncs = {{"downstream_fn", "umq"}};
    rel.downstreamNameIndex["downstream_fn"] = {0};
    collector.graph_.keyFuncRelevanceMap_["umq_ub_post_tx"] = rel;

    failure::FailureEvent evBase = MakeUmqEvent(T0, "umq_ub_post_tx");
    failure::FailureEvent evUp = MakeUmqEvent(T0, "upstream_fn");
    failure::FailureEvent evDown = MakeUmqEvent(T0, "downstream_fn");
    failure::FailureEvent evOther = MakeUmqEvent(T0, "unrelated_fn");
    failure::FailureEvent evNoAttr{};
    evNoAttr.timestamp = T0;

    failure::FailureMetadata meta;
    meta.funcName = "umq_ub_post_tx";
    meta.events = {nullptr, &evNoAttr, &evOther, &evBase, &evUp, &evDown};
    std::vector<failure::FailureMetadata> metadata = {meta};
    collector.FilterFuncNames(metadata);
    // 保留：基函数 + 上下游；剔除：空指针 / 无 function_name / 无关函数
    ASSERT_EQ(metadata[0].events.size(), 3u);
    EXPECT_EQ(metadata[0].events[0], &evBase);
    EXPECT_EQ(metadata[0].events[1], &evUp);
    EXPECT_EQ(metadata[0].events[2], &evDown);
}

TEST(CollectorCorrelate, NoUmqEventsEarlyReturn)
{
    failure::log::LogCollector collector;
    std::unordered_map<std::string, std::vector<failure::FailureEvent>> eventsMap;
    eventsMap["ubsocket"] = {MakeEvent("ubsocket", T0)};
    failure::FailureMetadata existing;
    existing.funcName = "keep";
    collector.metadata_ = {existing};
    EXPECT_EQ(collector.CorrelateEvents(eventsMap), RACK_OK);
    // 无 umq 事件：提前返回，metadata_ 不变
    ASSERT_EQ(collector.metadata_.size(), 1u);
    EXPECT_EQ(collector.metadata_[0].funcName, "keep");
}

TEST(CollectorCorrelate, FullPipeline)
{
    failure::log::LogCollector collector;
    collector.keyFuncEventTypeMap_ = &failure::keyFuncEventTypeMap;
    collector.keyFuncRoleMap_ = &failure::keyFuncRoleMap;

    // umq 关键事件：告警级别不符 / 非关键函数 / post(带端点) / bind
    failure::FailureEvent evWarn = MakeUmqEvent(T0, "umq_ub_post_tx", "other_proc");
    evWarn.attributes["alarm_level"] = "warn";
    failure::FailureEvent evUnknownFunc = MakeUmqEvent(T0, "not_a_key_func", "other_proc");
    failure::FailureEvent evPost = MakeBiEndpointUmqEvent(T0);
    failure::FailureEvent evBind = MakeUmqEvent(T0 + 1000, "umq_ub_bind_inner_impl");

    // ubsocket 资源域事件：窗口内/外
    failure::FailureEvent ubIn = MakeEvent("ubsocket", T0 + 5 * 1000 * 1000LL);
    failure::FailureEvent ubOut = MakeEvent("ubsocket", T0 + 11 * 1000 * 1000LL);
    // urmacore：窗口内
    failure::FailureEvent urmaIn = MakeEvent("urmacore", T0 - 5 * 1000 * 1000LL);
    // hardware：跳过
    failure::FailureEvent hw = MakeEvent("hardware", T0);

    std::unordered_map<std::string, std::vector<failure::FailureEvent>> eventsMap;
    eventsMap["umq"] = {evWarn, evUnknownFunc, evPost, evBind};
    eventsMap["ubsocket"] = {ubOut, ubIn};
    eventsMap["urmacore"] = {urmaIn};
    eventsMap["hardware"] = {hw};

    EXPECT_EQ(collector.CorrelateEvents(eventsMap), RACK_OK);
    ASSERT_EQ(collector.metadata_.size(), 2u);
    // 按时间排序：post 在前
    const failure::FailureMetadata &post = collector.metadata_[0];
    const failure::FailureMetadata &bind = collector.metadata_[1];
    EXPECT_EQ(post.funcName, "umq_ub_post_tx");
    EXPECT_EQ(bind.funcName, "umq_ub_bind_inner_impl");
    EXPECT_TRUE(post.timestamp <= bind.timestamp);

    // post(窗口 [T0-10s, T0])：umq 同进程事件 evPost + urmacore 窗口内 + ubsocket 窗口内
    // evBind 在 T0+1000，落在 post 的 umq 窗口之外；evWarn/evUnknownFunc 进程不同且无端点
    ASSERT_EQ(post.events.size(), 3u);
    // bind(窗口 [T0+1000-10s, T0+1000])：umq 的 evPost/evBind 同进程 + ub 窗口内 + urma 窗口内
    ASSERT_EQ(bind.events.size(), 4u);

    // 视图已构建：两个顶函数视图
    EXPECT_EQ(collector.view_.root_["callstack_views"].size(), 2u);
    EXPECT_EQ(collector.view_.root_["resource_views"].size(), 2u);
}

// ---------- 生命周期入口 ----------

TEST(CollectorLifecycle, InitializeFailsWithoutVarDir)
{
    failure::log::LogCollector collector;
    // /var/witty-ub 不可写 -> InitIO 失败
    EXPECT_EQ(collector.Initialize(), RACK_FAIL);
}

TEST(CollectorLifecycle, StartStopWithoutReaders)
{
    failure::log::LogCollector collector;
    // 无 reader：工具模式下 Start 跑一轮空关联并保存（输出失败被容忍），返回成功
    EXPECT_EQ(collector.Start(), RACK_OK);
    EXPECT_TRUE(collector.metadata_.empty());
    EXPECT_TRUE(collector.workerThreads_.empty());
    collector.Stop();
    // 可重复启停
    EXPECT_EQ(collector.Start(), RACK_OK);
    collector.Stop();
}

TEST(CollectorLifecycle, SaveSwapsMetadataAndToleratesUnwritableOutput)
{
    failure::log::LogCollector collector;
    failure::FailureMetadata meta;
    meta.funcName = "umq_ub_post_tx";
    meta.programName = "umq_proc";
    collector.metadata_ = {meta};
    // /var/witty-ub/failure_event.json 打不开：记录日志后返回，不崩溃
    collector.Save();
    // metadata_ 被 swap 走
    EXPECT_TRUE(collector.metadata_.empty());
}
