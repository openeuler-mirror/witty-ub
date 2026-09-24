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

// 测试目标：src/brpc_diag_tool/log_collector.cpp 与 src/brpc_diag_tool/diagnosis_module.cpp

#include <gtest/gtest.h>
#include <json/json.h>

#include <array>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <queue>
#include <sstream>
#include <string>
#include <string_view>
#include <typeindex>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "log_def.h"
#include "logger.h"
#include "rack_error.h"
#include "rack_module.h"

// 访问私有成员便于直测
#define private public
#include "log_collector.h"
#include "ubse_context.h"
#include "diagnosis_module.h"
#undef private

namespace {

// 被测实现打日志走 log4cplus，必须先初始化，否则崩溃。
struct LoggerInit {
    LoggerInit() { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

// RAII 临时目录
class TempDir {
public:
    explicit TempDir(const std::string &prefix)
    {
        static int counter = 0;
        dir_ = std::filesystem::temp_directory_path() /
               (prefix + "_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) + "_" +
                std::to_string(counter++));
        std::filesystem::create_directories(dir_);
    }
    ~TempDir() { std::filesystem::remove_all(dir_); }

    const std::filesystem::path &Path() const { return dir_; }

    void Write(const std::string &relPath, const std::string &content)
    {
        std::filesystem::create_directories((dir_ / relPath).parent_path());
        std::ofstream out(dir_ / relPath);
        out << content;
    }

private:
    std::filesystem::path dir_;
};

// 日志时间戳格式：[YYYYMMDD HH:MM:SS.uuuuuu]（东八区）
constexpr const char *TS0_TEXT = "20260101 12:00:00.000000";
constexpr std::int64_t TS0 = 1767240000000000;
constexpr const char *TS1_TEXT = "20260101 12:00:01.500000"; // TS0 + 1500000
constexpr const char *TS2_TEXT = "20260101 12:00:02.000000"; // TS0 + 2000000
constexpr const char *EARLY_TEXT = "20260101 11:59:59.999999"; // TS0 - 1

std::string MakeLogLine(const std::string &timestampText, const std::string &pod = "pod-1",
                        const std::string &ip = "10.0.0.1", const std::string &component = "UBSOCKET",
                        const std::string &location = "err.cpp:ErrFunc:42", const std::string &thread = "123",
                        const std::string &trace = "trace-1", const std::string &message = "an error occurred")
{
    return "[" + timestampText + "][" + pod + "][" + ip + "][" + component + "][" + location + "][" + thread + "][" +
           trace + "]" + message;
}

std::vector<brpc::BrpcLog> CollectAll(const brpc::LogCollector &collector, std::int64_t start, std::int64_t end)
{
    std::vector<brpc::BrpcLog> logs;
    collector.ForEachBrpcLog(start, end, [&logs](brpc::BrpcLog &&log) { logs.push_back(std::move(log)); });
    return logs;
}

} // namespace

// ---------------------------------------------------------------------------
// ParseNonnegativeInt
// ---------------------------------------------------------------------------

TEST(LogCollectorParseInt, ParsesValidNumbers) {
    int value = -1;
    EXPECT_TRUE(brpc::LogCollector::ParseNonnegativeInt("12345", value));
    EXPECT_EQ(value, 12345);
    EXPECT_TRUE(brpc::LogCollector::ParseNonnegativeInt("0", value));
    EXPECT_EQ(value, 0);
    EXPECT_TRUE(brpc::LogCollector::ParseNonnegativeInt("2147483647", value)); // INT_MAX
    EXPECT_EQ(value, 2147483647);
}

TEST(LogCollectorParseInt, RejectsInvalidInput) {
    int value = 0;
    EXPECT_FALSE(brpc::LogCollector::ParseNonnegativeInt("", value));
    EXPECT_FALSE(brpc::LogCollector::ParseNonnegativeInt("12a4", value));
    EXPECT_FALSE(brpc::LogCollector::ParseNonnegativeInt("-1", value));
    EXPECT_FALSE(brpc::LogCollector::ParseNonnegativeInt(" 1", value));
    EXPECT_FALSE(brpc::LogCollector::ParseNonnegativeInt("2147483648", value)); // 溢出
}

// ---------------------------------------------------------------------------
// ParseLogTimestamp
// ---------------------------------------------------------------------------

TEST(LogCollectorParseTimestamp, ParsesValidTimestamp) {
    std::int64_t timestamp = 0;
    EXPECT_TRUE(brpc::LogCollector::ParseLogTimestamp("20260101 12:00:00.000000", timestamp));
    EXPECT_EQ(timestamp, TS0);
    EXPECT_TRUE(brpc::LogCollector::ParseLogTimestamp("20240229 00:00:00.000000", timestamp)); // 闰年
}

TEST(LogCollectorParseTimestamp, RejectsWrongLength) {
    std::int64_t timestamp = 0;
    EXPECT_FALSE(brpc::LogCollector::ParseLogTimestamp("20260101 12:00:00.00000", timestamp));   // 23 字符
    EXPECT_FALSE(brpc::LogCollector::ParseLogTimestamp("20260101 12:00:00.0000000", timestamp)); // 25 字符
}

TEST(LogCollectorParseTimestamp, RejectsBadSeparators) {
    std::int64_t timestamp = 0;
    EXPECT_FALSE(brpc::LogCollector::ParseLogTimestamp("2026010112:00:00.000000", timestamp)); // 位置 8 非空格
    EXPECT_FALSE(brpc::LogCollector::ParseLogTimestamp("20260101 12x00:00.000000", timestamp)); // 位置 11 非 ':'
    EXPECT_FALSE(brpc::LogCollector::ParseLogTimestamp("20260101 12:00x00.000000", timestamp)); // 位置 14 非 ':'
    EXPECT_FALSE(brpc::LogCollector::ParseLogTimestamp("20260101 12:00:00x000000", timestamp)); // 位置 17 非 '.'
}

TEST(LogCollectorParseTimestamp, RejectsNonDigitField) {
    std::int64_t timestamp = 0;
    EXPECT_FALSE(brpc::LogCollector::ParseLogTimestamp("202a0101 12:00:00.000000", timestamp));
}

TEST(LogCollectorParseTimestamp, RejectsInvalidCivilTime) {
    std::int64_t timestamp = 0;
    EXPECT_FALSE(brpc::LogCollector::ParseLogTimestamp("20261301 12:00:00.000000", timestamp)); // 月 13
    EXPECT_FALSE(brpc::LogCollector::ParseLogTimestamp("20260132 12:00:00.000000", timestamp)); // 日 32
    EXPECT_FALSE(brpc::LogCollector::ParseLogTimestamp("20230229 12:00:00.000000", timestamp)); // 非闰年
    EXPECT_FALSE(brpc::LogCollector::ParseLogTimestamp("20260101 24:00:00.000000", timestamp)); // 时 24
    EXPECT_FALSE(brpc::LogCollector::ParseLogTimestamp("20260101 12:60:00.000000", timestamp)); // 分 60
    EXPECT_FALSE(brpc::LogCollector::ParseLogTimestamp("20260101 12:00:60.000000", timestamp)); // 秒 60
}

// ---------------------------------------------------------------------------
// ExtractLogTimestamp
// ---------------------------------------------------------------------------

TEST(LogCollectorExtractTimestamp, ExtractsFromBracketedPrefix) {
    std::int64_t timestamp = 0;
    EXPECT_TRUE(brpc::LogCollector::ExtractLogTimestamp(std::string("[") + TS0_TEXT + "]rest of line", timestamp));
    EXPECT_EQ(timestamp, TS0);
    // 恰好只有时间戳括号（26 字符）也可解析
    EXPECT_TRUE(brpc::LogCollector::ExtractLogTimestamp(std::string("[") + TS0_TEXT + "]", timestamp));
}

TEST(LogCollectorExtractTimestamp, RejectsMalformedPrefix) {
    std::int64_t timestamp = 0;
    EXPECT_FALSE(brpc::LogCollector::ExtractLogTimestamp(std::string(TS0_TEXT) + "]tail", timestamp)); // 缺 '['
    EXPECT_FALSE(brpc::LogCollector::ExtractLogTimestamp(std::string("[") + TS0_TEXT + "tail", timestamp)); // 缺 ']'
    EXPECT_FALSE(brpc::LogCollector::ExtractLogTimestamp(std::string("[") + TS0_TEXT, timestamp)); // 长度不足
    EXPECT_FALSE(brpc::LogCollector::ExtractLogTimestamp(std::string("[20260101 12:00:00.00000]x"), timestamp)); // 坏时间
}

// ---------------------------------------------------------------------------
// ParseLocation
// ---------------------------------------------------------------------------

TEST(LogCollectorParseLocation, ParsesFilenameFunctionLine) {
    std::string filename;
    std::string functionName;
    int lineNo = 0;
    EXPECT_TRUE(brpc::LogCollector::ParseLocation("err.cpp:ErrFunc:42", filename, functionName, lineNo));
    EXPECT_EQ(filename, "err.cpp");
    EXPECT_EQ(functionName, "ErrFunc");
    EXPECT_EQ(lineNo, 42);
}

TEST(LogCollectorParseLocation, RejectsMalformedLocation) {
    std::string filename;
    std::string functionName;
    int lineNo = 0;
    EXPECT_FALSE(brpc::LogCollector::ParseLocation("plainlocation", filename, functionName, lineNo)); // 无 ':'
    EXPECT_FALSE(brpc::LogCollector::ParseLocation("err.cpp:42", filename, functionName, lineNo)); // 单 ':'
    EXPECT_FALSE(brpc::LogCollector::ParseLocation(":Func:42", filename, functionName, lineNo)); // 空文件名
    EXPECT_FALSE(brpc::LogCollector::ParseLocation("err.cpp:Func:", filename, functionName, lineNo)); // 尾 ':'
    EXPECT_FALSE(brpc::LogCollector::ParseLocation("err.cpp::42", filename, functionName, lineNo)); // 空函数名
    EXPECT_FALSE(brpc::LogCollector::ParseLocation("err.cpp:Func:abc", filename, functionName, lineNo)); // 非数字
    EXPECT_FALSE(brpc::LogCollector::ParseLocation("err.cpp:Func:-1", filename, functionName, lineNo)); // 负数
    EXPECT_FALSE(brpc::LogCollector::ParseLocation("err.cpp:Func:2147483648", filename, functionName, lineNo)); // 溢出
}

// ---------------------------------------------------------------------------
// ParseThreadId / ParseTraceId
// ---------------------------------------------------------------------------

TEST(LogCollectorParseThreadId, HandlesDashNumberAndInvalid) {
    std::optional<int> threadId = 0;
    EXPECT_TRUE(brpc::LogCollector::ParseThreadId("-", threadId));
    EXPECT_FALSE(threadId.has_value());
    EXPECT_TRUE(brpc::LogCollector::ParseThreadId("77", threadId));
    ASSERT_TRUE(threadId.has_value());
    EXPECT_EQ(*threadId, 77);
    EXPECT_FALSE(brpc::LogCollector::ParseThreadId("", threadId));
    EXPECT_FALSE(brpc::LogCollector::ParseThreadId("abc", threadId));
    EXPECT_FALSE(brpc::LogCollector::ParseThreadId("-5", threadId));
}

TEST(LogCollectorParseTraceId, HandlesDashStringAndEmpty) {
    std::optional<std::string> traceId;
    EXPECT_TRUE(brpc::LogCollector::ParseTraceId("-", traceId));
    EXPECT_FALSE(traceId.has_value());
    EXPECT_TRUE(brpc::LogCollector::ParseTraceId("trace-1", traceId));
    ASSERT_TRUE(traceId.has_value());
    EXPECT_EQ(*traceId, "trace-1");
    EXPECT_FALSE(brpc::LogCollector::ParseTraceId("", traceId));
}

// ---------------------------------------------------------------------------
// ExtractBracketFields / ParseUrmaLogFields
// ---------------------------------------------------------------------------

TEST(LogCollectorBracketFields, ExtractsFieldsAndMessageOffset) {
    // 模板定义在 log_collector.cpp 中，仅有 4（URMA）/ 7（BRPC）两处显式实例化
    std::array<std::string_view, 4> fields;
    std::size_t offset = 0;
    EXPECT_TRUE(brpc::LogCollector::ExtractBracketFields("[a][bb][ccc][dddd]message", fields, offset));
    EXPECT_EQ(fields[0], "a");
    EXPECT_EQ(fields[1], "bb");
    EXPECT_EQ(fields[2], "ccc");
    EXPECT_EQ(fields[3], "dddd");
    EXPECT_EQ(offset, 18u);
}

TEST(LogCollectorBracketFields, RejectsMalformedBrackets) {
    std::array<std::string_view, 4> fields;
    std::size_t offset = 0;
    EXPECT_FALSE(brpc::LogCollector::ExtractBracketFields("a][b][c][d]", fields, offset)); // 缺 '['
    EXPECT_FALSE(brpc::LogCollector::ExtractBracketFields("[a][b][c][d", fields, offset)); // 缺 ']'
    EXPECT_FALSE(brpc::LogCollector::ExtractBracketFields("", fields, offset));
}

TEST(LogCollectorUrmaFields, ParsesValidInnerLog) {
    brpc::LogCollector::UrmaLogFields fields;
    EXPECT_TRUE(brpc::LogCollector::ParseUrmaLogFields("[URMA][thread_id=42][trace-1][u.cpp:FuncU:7]urma fail",
                                                       fields));
    EXPECT_EQ(fields.filename, "u.cpp");
    EXPECT_EQ(fields.functionName, "FuncU");
    EXPECT_EQ(fields.lineNo, 7);
    ASSERT_TRUE(fields.threadId.has_value());
    EXPECT_EQ(*fields.threadId, 42);
    ASSERT_TRUE(fields.traceId.has_value());
    EXPECT_EQ(*fields.traceId, "trace-1");
}

TEST(LogCollectorUrmaFields, RejectsMalformedInnerLog) {
    brpc::LogCollector::UrmaLogFields fields;
    EXPECT_FALSE(brpc::LogCollector::ParseUrmaLogFields("[URMA][thread_id=42][trace-1]", fields)); // 括号不足
    EXPECT_FALSE(brpc::LogCollector::ParseUrmaLogFields("[URMA][tid=42][t][u.cpp:F:1]m", fields)); // 前缀不符
    EXPECT_FALSE(brpc::LogCollector::ParseUrmaLogFields("[URMA][thread_id=-][t][u.cpp:F:1]m", fields)); // 无 tid
    EXPECT_FALSE(brpc::LogCollector::ParseUrmaLogFields("[URMA][thread_id=abc][t][u.cpp:F:1]m", fields)); // 非数字
    EXPECT_FALSE(brpc::LogCollector::ParseUrmaLogFields("[URMA][thread_id=1][t][bad]m", fields)); // 坏位置
    EXPECT_FALSE(brpc::LogCollector::ParseUrmaLogFields("[URMA][thread_id=1][][u.cpp:F:1]m", fields)); // 空 trace
}

TEST(LogCollectorUrmaFields, AcceptsDashTraceId) {
    brpc::LogCollector::UrmaLogFields fields;
    EXPECT_TRUE(brpc::LogCollector::ParseUrmaLogFields("[URMA][thread_id=1][-][u.cpp:F:1]m", fields));
    EXPECT_FALSE(fields.traceId.has_value());
}

// ---------------------------------------------------------------------------
// ParseBrpcLogFields
// ---------------------------------------------------------------------------

TEST(LogCollectorBrpcFields, ParsesFullLine) {
    brpc::BrpcLog logEntry;
    logEntry.text = MakeLogLine(TS0_TEXT);
    ASSERT_TRUE(brpc::LogCollector::ParseBrpcLogFields(logEntry));
    EXPECT_EQ(logEntry.podName, "pod-1");
    EXPECT_EQ(logEntry.podIp, "10.0.0.1");
    EXPECT_EQ(logEntry.component, "UBSOCKET");
    EXPECT_EQ(logEntry.filename, "err.cpp");
    EXPECT_EQ(logEntry.functionName, "ErrFunc");
    EXPECT_EQ(logEntry.lineNo, 42);
    ASSERT_TRUE(logEntry.threadId.has_value());
    EXPECT_EQ(*logEntry.threadId, 123);
    ASSERT_TRUE(logEntry.traceId.has_value());
    EXPECT_EQ(*logEntry.traceId, "trace-1");
    EXPECT_EQ(logEntry.message, "an error occurred");
}

TEST(LogCollectorBrpcFields, AcceptsDashThreadAndTrace) {
    brpc::BrpcLog logEntry;
    logEntry.text = MakeLogLine(TS0_TEXT, "pod", "ip", "UBSOCKET", "err.cpp:ErrFunc:42", "-", "-", "msg");
    ASSERT_TRUE(brpc::LogCollector::ParseBrpcLogFields(logEntry));
    EXPECT_FALSE(logEntry.threadId.has_value());
    EXPECT_FALSE(logEntry.traceId.has_value());
}

TEST(LogCollectorBrpcFields, ParsesUrmaInnerLog) {
    brpc::BrpcLog logEntry;
    logEntry.text = MakeLogLine(TS0_TEXT, "pod", "ip", "UBSOCKET", "outer.cpp:OuterFunc:9", "5", "outer-trace",
                                "[URMA][thread_id=42][trace-1][u.cpp:FuncU:7]urma fail detected");
    ASSERT_TRUE(brpc::LogCollector::ParseBrpcLogFields(logEntry));
    EXPECT_EQ(logEntry.component, "URMA");
    EXPECT_EQ(logEntry.filename, "u.cpp");
    EXPECT_EQ(logEntry.functionName, "FuncU");
    EXPECT_EQ(logEntry.lineNo, 7);
    ASSERT_TRUE(logEntry.threadId.has_value());
    EXPECT_EQ(*logEntry.threadId, 42);
    ASSERT_TRUE(logEntry.traceId.has_value());
    EXPECT_EQ(*logEntry.traceId, "trace-1");
    // URMA 日志头保留在正文中，用于故障模式匹配
    EXPECT_EQ(logEntry.message, "[URMA][thread_id=42][trace-1][u.cpp:FuncU:7]urma fail detected");
}

TEST(LogCollectorBrpcFields, RejectsMalformedLines) {
    brpc::BrpcLog logEntry;
    // 括号字段不足 7 个
    logEntry.text = "[" + std::string(TS0_TEXT) + "][pod][ip][UBSOCKET][err.cpp:ErrFunc:42][123]";
    EXPECT_FALSE(brpc::LogCollector::ParseBrpcLogFields(logEntry));
    // 位置字段格式错误
    logEntry.text = MakeLogLine(TS0_TEXT, "pod", "ip", "UBSOCKET", "nocolon", "123", "tr", "msg");
    EXPECT_FALSE(brpc::LogCollector::ParseBrpcLogFields(logEntry));
    // 线程号非数字
    logEntry.text = MakeLogLine(TS0_TEXT, "pod", "ip", "UBSOCKET", "err.cpp:ErrFunc:42", "abc", "tr", "msg");
    EXPECT_FALSE(brpc::LogCollector::ParseBrpcLogFields(logEntry));
    // trace 为空
    logEntry.text = MakeLogLine(TS0_TEXT, "pod", "ip", "UBSOCKET", "err.cpp:ErrFunc:42", "123", "", "msg");
    EXPECT_FALSE(brpc::LogCollector::ParseBrpcLogFields(logEntry));
    // 内层 URMA 日志格式错误
    logEntry.text = MakeLogLine(TS0_TEXT, "pod", "ip", "UBSOCKET", "outer.cpp:OuterFunc:9", "5", "tr",
                                "[URMA][thread_id=-][t][u.cpp:F:1]m");
    EXPECT_FALSE(brpc::LogCollector::ParseBrpcLogFields(logEntry));
}

// ---------------------------------------------------------------------------
// CurrentTimestamp
// ---------------------------------------------------------------------------

TEST(LogCollectorTimestamp, CurrentTimestampIsMonotonicMicroseconds) {
    const std::int64_t first = brpc::LogCollector::CurrentTimestamp();
    const std::int64_t second = brpc::LogCollector::CurrentTimestamp();
    EXPECT_GE(second, first);
    EXPECT_GT(first, 1700000000000000); // 2023-11 之后
}

// ---------------------------------------------------------------------------
// ForEachBrpcLog
// ---------------------------------------------------------------------------

TEST(LogCollectorForEach, FailsOnMissingPath) {
    TempDir dir("brpclc_missing");
    const brpc::LogCollector collector(dir.Path() / "nonexistent.log");
    EXPECT_FALSE(collector.ForEachBrpcLog(0, TS0 + 1000000, [](brpc::BrpcLog &&) {}));
}

TEST(LogCollectorForEach, FailsOnEmptyDirectory) {
    TempDir dir("brpclc_emptydir");
    const brpc::LogCollector collector(dir.Path());
    EXPECT_FALSE(collector.ForEachBrpcLog(0, TS0 + 1000000, [](brpc::BrpcLog &&) {}));
}

TEST(LogCollectorForEach, EmptyWindowReturnsTrueWithoutLogs) {
    TempDir dir("brpclc_emptywin");
    dir.Write("brpc.log", std::string(MakeLogLine(TS0_TEXT)) + "\n");
    const brpc::LogCollector collector(dir.Path() / "brpc.log");
    EXPECT_TRUE(collector.ForEachBrpcLog(500, 500, [](brpc::BrpcLog &&) { FAIL() << "不应回调"; }));
    EXPECT_TRUE(collector.ForEachBrpcLog(600, 500, [](brpc::BrpcLog &&) { FAIL() << "不应回调"; }));
}

TEST(LogCollectorForEach, ReadsSingleFileWithFiltering) {
    TempDir dir("brpclc_single");
    dir.Write("brpc.log",
              std::string(MakeLogLine(TS0_TEXT)) + "\n" +                     // 窗内
                  std::string(MakeLogLine(EARLY_TEXT)) + "\n" +               // 早于窗
                  std::string("garbage line without timestamp") + "\n" +      // 无效时间戳
                  std::string(MakeLogLine(TS2_TEXT)) + "\n" +                 // == end，窗外
                  std::string(MakeLogLine(TS1_TEXT, "pod-2", "10.0.0.2", "UMQ", "umq.cpp:UmqFunc:7", "9", "t2",
                                          "umq fail")) + "\n");               // 窗内
    const brpc::LogCollector collector(dir.Path() / "brpc.log");
    const auto logs = CollectAll(collector, TS0, TS0 + 2000000);
    ASSERT_EQ(logs.size(), 2u);

    EXPECT_EQ(logs[0].timestamp, TS0);
    EXPECT_EQ(logs[0].podName, "pod-1");
    EXPECT_EQ(logs[0].podIp, "10.0.0.1");
    EXPECT_EQ(logs[0].component, "UBSOCKET");
    EXPECT_EQ(logs[0].filename, "err.cpp");
    EXPECT_EQ(logs[0].functionName, "ErrFunc");
    EXPECT_EQ(logs[0].lineNo, 42);
    ASSERT_TRUE(logs[0].threadId.has_value());
    EXPECT_EQ(*logs[0].threadId, 123);
    ASSERT_TRUE(logs[0].traceId.has_value());
    EXPECT_EQ(*logs[0].traceId, "trace-1");
    EXPECT_EQ(logs[0].message, "an error occurred");

    EXPECT_EQ(logs[1].timestamp, TS0 + 1500000);
    EXPECT_EQ(logs[1].component, "UMQ");
    EXPECT_EQ(logs[1].message, "umq fail");
}

TEST(LogCollectorForEach, RecursesDirectoryInSortedOrder) {
    TempDir dir("brpclc_dir");
    dir.Write("b.log", std::string(MakeLogLine(TS0_TEXT, "pod", "ip", "UBSOCKET", "err.cpp:ErrFunc:42", "1", "t",
                                               "in b")) +
                           "\n");
    dir.Write("a.log", std::string(MakeLogLine(TS0_TEXT, "pod", "ip", "UBSOCKET", "err.cpp:ErrFunc:42", "1", "t",
                                               "in a")) +
                           "\n");
    dir.Write("sub/c.log", std::string(MakeLogLine(TS0_TEXT, "pod", "ip", "UBSOCKET", "err.cpp:ErrFunc:42", "1", "t",
                                                   "in c")) +
                               "\n");
    const brpc::LogCollector collector(dir.Path());
    const auto logs = CollectAll(collector, TS0, TS0 + 1000000);
    ASSERT_EQ(logs.size(), 3u);
    EXPECT_EQ(logs[0].message, "in a");
    EXPECT_EQ(logs[1].message, "in b");
    EXPECT_EQ(logs[2].message, "in c");
}

TEST(LogCollectorForEach, RetainsInvalidFormatAsRawText) {
    TempDir dir("brpclc_raw");
    const std::string line = "[" + std::string(TS0_TEXT) + "]garbage without bracket fields";
    dir.Write("brpc.log", line + "\n");
    const brpc::LogCollector collector(dir.Path() / "brpc.log");
    const auto logs = CollectAll(collector, TS0, TS0 + 1000000);
    ASSERT_EQ(logs.size(), 1u);
    // 解析失败但时间戳有效 → 按原文保留
    EXPECT_EQ(logs[0].text, line);
    EXPECT_EQ(logs[0].timestamp, TS0);
    EXPECT_TRUE(logs[0].podName.empty());
    EXPECT_TRUE(logs[0].filename.empty());
    EXPECT_TRUE(logs[0].message.empty());
}

TEST(LogCollectorForEach, ParsesUrmaLines) {
    TempDir dir("brpclc_urma");
    const std::string line = MakeLogLine(TS0_TEXT, "pod", "ip", "UBSOCKET", "outer.cpp:OuterFunc:9", "5", "tr",
                                         "[URMA][thread_id=42][trace-1][u.cpp:FuncU:7]urma fail detected");
    dir.Write("brpc.log", line + "\n");
    const brpc::LogCollector collector(dir.Path() / "brpc.log");
    const auto logs = CollectAll(collector, TS0, TS0 + 1000000);
    ASSERT_EQ(logs.size(), 1u);
    EXPECT_EQ(logs[0].component, "URMA");
    EXPECT_EQ(logs[0].filename, "u.cpp");
    EXPECT_EQ(logs[0].functionName, "FuncU");
    EXPECT_EQ(logs[0].lineNo, 7);
    ASSERT_TRUE(logs[0].threadId.has_value());
    EXPECT_EQ(*logs[0].threadId, 42);
}

// ---------------------------------------------------------------------------
// DiagnosisModule：模块生命周期
// ---------------------------------------------------------------------------

namespace {

// 全 local 边规则树：每个故障模式都能经同组件 publicApi 到达（Build 的硬约束）
const char *MOD_UBSOCKET_JSON = R"([
    {"故障编号":"ubsocket_root","故障名称":"root","文件名":"root.cpp","故障现象":"向下级匹配",
     "故障原因":"c1","解决办法":"s1","函数名":"RootFunc","错误码":1001},
    {"故障编号":"ubsocket_err","故障名称":"err","文件名":"err.cpp","故障现象":"依次匹配`error`、`timeout`",
     "故障原因":"c2","解决办法":"s2","函数名":"ErrFunc","错误码":"E002"}
])";
const char *MOD_UMQ_JSON = R"([
    {"故障编号":"umq_root","故障名称":"uroot","文件名":"umq_root.cpp","故障现象":"向下级匹配",
     "故障原因":"c3","解决办法":"s3","函数名":"UmqRootFunc"},
    {"故障编号":"umq_err","故障名称":"uerr","文件名":"umq.cpp","故障现象":"依次匹配`umq fail`",
     "故障原因":"c4","解决办法":"s4","函数名":"UmqFunc"}
])";
const char *MOD_URMA_JSON = R"([
    {"故障编号":"urma_root","故障名称":"vroot","文件名":"urma_root.cpp","故障现象":"向下级匹配",
     "故障原因":"c5","解决办法":"s5","函数名":"UrmaRootFunc"},
    {"故障编号":"urma_err","故障名称":"verr","文件名":"urma.cpp","故障现象":"依次匹配`urma fail`",
     "故障原因":"c6","解决办法":"s6","函数名":"UrmaFunc"}
])";
const char *MOD_TREE_JSON = R"({
    "ubsocket": {"ubsocket_root": ["ubsocket_err"]},
    "umq": {"umq_root": ["umq_err"]},
    "urma": {"urma_root": ["urma_err"]}
})";

void WriteModuleRules(TempDir &wittyDir)
{
    wittyDir.Write("data/ubsocket/ubsocket_failure_mode.json", MOD_UBSOCKET_JSON);
    wittyDir.Write("data/umq/umq_failure_mode.json", MOD_UMQ_JSON);
    wittyDir.Write("data/urma/urma_failure_mode.json", MOD_URMA_JSON);
    wittyDir.Write("data/failure_mode_tree.json", MOD_TREE_JSON);
}

// 直接覆盖单例 argMap（ParseArgs 无法删除残留键，也无法传 '-' 开头的值）
void SetModuleArgs(std::initializer_list<std::pair<std::string, std::string>> args)
{
    auto &argMap = ubse::context::UbseContext::GetInstance().argMap;
    argMap.clear();
    for (const auto &argument : args) {
        argMap[argument.first] = argument.second;
    }
}

void SetWittyDir(const std::filesystem::path &path)
{
    ::setenv("WITTY_DIR", path.string().c_str(), 1);
}

const char *HIT_LINE =
    "[20260101 12:00:00.000000][pod-1][10.0.0.1][UBSOCKET][err.cpp:ErrFunc:42][123][trace-1]error and timeout "
    "occurred";

} // namespace

TEST(DiagnosisModuleInit, FailsWithoutBrpcLogArg) {
    TempDir witty("diagmod_brpc_witty");
    WriteModuleRules(witty);
    TempDir logs("diagmod_brpc_logs");
    logs.Write("brpc.log", std::string(HIT_LINE) + "\n");

    SetWittyDir(witty.Path());
    SetModuleArgs({{"task-id", "task_1"}, {"timestamp", "0"}});
    brpc::DiagnosisModule module;
    EXPECT_NE(module.Initialize(), RACK_OK);
}

TEST(DiagnosisModuleInit, FailsOnMissingBrpcLogPath) {
    TempDir witty("diagmod_brpcpath_witty");
    WriteModuleRules(witty);
    SetWittyDir(witty.Path());
    SetModuleArgs({{"brpc-log", (witty.Path() / "nonexistent.log").string()},
                   {"task-id", "task_1"},
                   {"timestamp", "0"}});
    brpc::DiagnosisModule module;
    EXPECT_NE(module.Initialize(), RACK_OK);
}

TEST(DiagnosisModuleInit, FailsWithoutTaskId) {
    TempDir witty("diagmod_tid_witty");
    WriteModuleRules(witty);
    TempDir logs("diagmod_tid_logs");
    logs.Write("brpc.log", std::string(HIT_LINE) + "\n");
    SetWittyDir(witty.Path());
    SetModuleArgs({{"brpc-log", (logs.Path() / "brpc.log").string()}, {"timestamp", "0"}});
    brpc::DiagnosisModule module;
    EXPECT_NE(module.Initialize(), RACK_OK);
}

TEST(DiagnosisModuleInit, FailsOnInvalidTaskId) {
    TempDir witty("diagmod_badtid_witty");
    WriteModuleRules(witty);
    TempDir logs("diagmod_badtid_logs");
    logs.Write("brpc.log", std::string(HIT_LINE) + "\n");
    SetWittyDir(witty.Path());
    const std::string logPath = (logs.Path() / "brpc.log").string();

    brpc::DiagnosisModule module;
    // 空串
    SetModuleArgs({{"brpc-log", logPath}, {"task-id", ""}, {"timestamp", "0"}});
    EXPECT_NE(module.Initialize(), RACK_OK);
    // 非法字符
    SetModuleArgs({{"brpc-log", logPath}, {"task-id", "bad id!"}, {"timestamp", "0"}});
    EXPECT_NE(module.Initialize(), RACK_OK);
    // 超长（>128）
    SetModuleArgs({{"brpc-log", logPath}, {"task-id", std::string(129, 'a')}, {"timestamp", "0"}});
    EXPECT_NE(module.Initialize(), RACK_OK);
}

TEST(DiagnosisModuleInit, FailsOnInvalidTimestamp) {
    TempDir witty("diagmod_badts_witty");
    WriteModuleRules(witty);
    TempDir logs("diagmod_badts_logs");
    logs.Write("brpc.log", std::string(HIT_LINE) + "\n");
    SetWittyDir(witty.Path());
    const std::string logPath = (logs.Path() / "brpc.log").string();

    brpc::DiagnosisModule module;
    // 非数字
    SetModuleArgs({{"brpc-log", logPath}, {"task-id", "task_1"}, {"timestamp", "abc"}});
    EXPECT_NE(module.Initialize(), RACK_OK);
    // 部分数字
    SetModuleArgs({{"brpc-log", logPath}, {"task-id", "task_1"}, {"timestamp", "12abc"}});
    EXPECT_NE(module.Initialize(), RACK_OK);
    // 溢出
    SetModuleArgs({{"brpc-log", logPath}, {"task-id", "task_1"}, {"timestamp", "99999999999999999999"}});
    EXPECT_NE(module.Initialize(), RACK_OK);
    // 负数
    SetModuleArgs({{"brpc-log", logPath}, {"task-id", "task_1"}, {"timestamp", "-5"}});
    EXPECT_NE(module.Initialize(), RACK_OK);
}

TEST(DiagnosisModuleInit, SucceedsWithValidArgs) {
    TempDir witty("diagmod_ok_witty");
    WriteModuleRules(witty);
    TempDir logs("diagmod_ok_logs");
    logs.Write("brpc.log", std::string(HIT_LINE) + "\n");

    SetWittyDir(witty.Path());
    SetModuleArgs({{"brpc-log", (logs.Path() / "brpc.log").string()},
                   {"task-id", "task_1"},
                   {"timestamp", "5000"}});
    brpc::DiagnosisModule module;
    EXPECT_EQ(module.Initialize(), RACK_OK);
    EXPECT_EQ(module.taskId_, "task_1");
    EXPECT_EQ(module.timestamp_, 5000);
    EXPECT_EQ(module.outputPath_, witty.Path() / "brpc-diag");
    EXPECT_NE(module.collector_, nullptr);
    EXPECT_NE(module.engine_, nullptr);

    module.Stop();
    module.UnInitialize();
}

TEST(DiagnosisModuleInit, TimestampDefaultsToZero) {
    TempDir witty("diagmod_nots_witty");
    WriteModuleRules(witty);
    TempDir logs("diagmod_nots_logs");
    logs.Write("brpc.log", std::string(HIT_LINE) + "\n");

    SetWittyDir(witty.Path());
    SetModuleArgs({{"brpc-log", (logs.Path() / "brpc.log").string()}, {"task-id", "task_1"}});
    brpc::DiagnosisModule module;
    EXPECT_EQ(module.Initialize(), RACK_OK);
    EXPECT_EQ(module.timestamp_, 0);

    module.UnInitialize();
}

TEST(DiagnosisModuleInit, FailsWhenEngineCannotLoadRules) {
    TempDir witty("diagmod_norule_witty"); // 空目录：无规则文件
    TempDir logs("diagmod_norule_logs");
    logs.Write("brpc.log", std::string(HIT_LINE) + "\n");

    SetWittyDir(witty.Path());
    SetModuleArgs({{"brpc-log", (logs.Path() / "brpc.log").string()},
                   {"task-id", "task_1"},
                   {"timestamp", "0"}});
    brpc::DiagnosisModule module;
    EXPECT_NE(module.Initialize(), RACK_OK);
    // 引擎创建失败时收集器一并释放
    EXPECT_EQ(module.collector_, nullptr);
    EXPECT_EQ(module.engine_, nullptr);
}

TEST(DiagnosisModuleLifecycle, StartFailsWithoutInitialize) {
    brpc::DiagnosisModule module;
    EXPECT_NE(module.Start(), RACK_OK);
}

TEST(DiagnosisModuleLifecycle, StopAndUninitializeSafeWithoutInit) {
    brpc::DiagnosisModule module;
    module.Stop();
    module.UnInitialize();
    SUCCEED();
}

TEST(DiagnosisModuleLifecycle, UninitializeClearsStateForRestart) {
    TempDir witty("diagmod_life_witty");
    WriteModuleRules(witty);
    TempDir logs("diagmod_life_logs");
    logs.Write("brpc.log", std::string(HIT_LINE) + "\n");

    SetWittyDir(witty.Path());
    SetModuleArgs({{"brpc-log", (logs.Path() / "brpc.log").string()},
                   {"task-id", "task_1"},
                   {"timestamp", "0"}});
    brpc::DiagnosisModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);
    EXPECT_EQ(module.Start(), RACK_OK);
    module.UnInitialize();
    EXPECT_EQ(module.collector_, nullptr);
    EXPECT_EQ(module.engine_, nullptr);
    EXPECT_TRUE(module.taskId_.empty());
    // 引擎清空后 Start 失败
    EXPECT_NE(module.Start(), RACK_OK);
    module.Stop();
}

TEST(DiagnosisModuleRun, StartSucceedsAndWritesOutputs) {
    TempDir witty("diagmod_run_witty");
    WriteModuleRules(witty);
    TempDir logs("diagmod_run_logs");
    logs.Write("brpc.log", std::string(HIT_LINE) + "\n");

    SetWittyDir(witty.Path());
    SetModuleArgs({{"brpc-log", (logs.Path() / "brpc.log").string()},
                   {"task-id", "task_1"},
                   {"timestamp", "0"}});
    brpc::DiagnosisModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);
    EXPECT_EQ(module.Start(), RACK_OK);

    const auto outputDir = witty.Path() / "brpc-diag";
    ASSERT_TRUE(std::filesystem::exists(outputDir / "batch_task_1.jsonl"));
    std::ifstream batch(outputDir / "batch_task_1.jsonl");
    std::stringstream buffer;
    buffer << batch.rdbuf();
    const std::string content = buffer.str();
    EXPECT_NE(content.find("\"record_type\":\"batch\""), std::string::npos);
    EXPECT_NE(content.find("ubsocket_err"), std::string::npos);

    bool hasSchema = false;
    for (const auto &entry : std::filesystem::directory_iterator(outputDir)) {
        if (entry.path().filename().string().rfind("schema_", 0) == 0) {
            hasSchema = true;
        }
    }
    EXPECT_TRUE(hasSchema);

    module.Stop();
    module.UnInitialize();
}

TEST(DiagnosisModuleRun, StartFailsWhenLogFileDisappears) {
    TempDir witty("diagmod_gone_witty");
    WriteModuleRules(witty);
    TempDir logs("diagmod_gone_logs");
    const auto logPath = logs.Path() / "brpc.log";
    logs.Write("brpc.log", std::string(HIT_LINE) + "\n");

    SetWittyDir(witty.Path());
    SetModuleArgs({{"brpc-log", logPath.string()}, {"task-id", "task_1"}, {"timestamp", "0"}});
    brpc::DiagnosisModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);
    std::filesystem::remove(logPath); // 收集路径失效 → RunDiagnosis 失败
    EXPECT_NE(module.Start(), RACK_OK);

    module.UnInitialize();
}

TEST(DiagnosisModuleRun, StartFailsWhenOutputDirBlocked) {
    TempDir witty("diagmod_block_witty");
    WriteModuleRules(witty);
    TempDir logs("diagmod_block_logs");
    logs.Write("brpc.log", ""); // 空日志：诊断成功，仅输出受阻

    SetWittyDir(witty.Path());
    SetModuleArgs({{"brpc-log", (logs.Path() / "brpc.log").string()},
                   {"task-id", "task_1"},
                   {"timestamp", "0"}});
    brpc::DiagnosisModule module;
    ASSERT_EQ(module.Initialize(), RACK_OK);
    // 用同名普通文件堵住输出目录 → Dump 失败
    witty.Write("brpc-diag", "x");
    EXPECT_NE(module.Start(), RACK_OK);

    module.UnInitialize();
}
