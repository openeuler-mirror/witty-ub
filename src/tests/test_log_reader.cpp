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

#include <sys/types.h>

#include <chrono>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <vector>

#include "temp_dir.h"
#include "log_reader.h"
#include "logger.h"

// log_reader 实现中打日志（LOG_ERROR 路径），log4cplus 必须先初始化
struct LoggerInit {
    LoggerInit() noexcept { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

namespace failure::log {
// log_reader.cpp 中的内部自由函数（外部链接），直接前向声明进行直测
std::string TrimCopy(const std::string &str);
bool HasKeywordChar(const std::string &str);
std::vector<std::string> ExtractManifestKeywords(const std::string &manifest);
std::vector<std::string> BuildKeywordFilter(const std::vector<std::string> &keywords);
void WaitForChildren(std::vector<pid_t> &childPids);
FILE *SpawnPipeline(std::vector<std::vector<std::string>> &commands, std::vector<pid_t> &childPids);
} // namespace failure::log

namespace {

// 每用例独立临时目录（公共实现见 temp_dir.h）

// 单行模板：形如 2024-01-15T10:30:01.123456+08:00|W|UMQ|消息
const char *SINGLE_MANIFEST = "<datetime>|<level>|UMQ|<content>";
// 多行模板：identifier 相同的相邻行合并
const char *MULTI_MANIFEST = "<datetime>|UMQ|<identifier>|<content>";
// 内核日志模板：syslog 时间戳整体落入 datetime 字段
const char *KERNEL_MANIFEST = "<datetime> umq: <content>";

// 时间窗口覆盖 2024-01-15 全天（微秒），确保 awk/gawk 两侧时区解释均在窗内
std::unique_ptr<failure::log::LogReader> MakeReader(failure::DataSourceOption option, const std::string &path,
                                                    const char *manifest, bool multiline = false)
{
    failure::FailureMode mode;
    mode.component = "umq";
    mode.version = "1.0";
    mode.isMultiline = multiline;
    mode.manifest = manifest;

    failure::PathCell cell;
    cell.path = path;
    auto start = failure::DatetimeStrToTimestamp("2024-01-15T00:00:00");
    auto end = failure::DatetimeStrToTimestamp("2024-01-15T23:59:59");
    auto reader = std::make_unique<failure::log::LogReader>(option, cell, *start, *end);
    reader->AddFailureMode(mode);
    return reader;
}

} // namespace

// ---------------------------------------------------------------------------
// 纯函数直测
// ---------------------------------------------------------------------------

TEST(TrimCopy, RemovesSurroundingWhitespace)
{
    EXPECT_EQ(failure::log::TrimCopy("  a b  "), "a b");
    EXPECT_EQ(failure::log::TrimCopy("\t\n x \r"), "x");
}

TEST(TrimCopy, AllWhitespaceAndEmpty)
{
    EXPECT_EQ(failure::log::TrimCopy("   "), "");
    EXPECT_EQ(failure::log::TrimCopy(""), "");
}

TEST(HasKeywordChar, DetectsAlnumAndUnderscore)
{
    EXPECT_TRUE(failure::log::HasKeywordChar("abc"));
    EXPECT_TRUE(failure::log::HasKeywordChar("  _9"));
    EXPECT_FALSE(failure::log::HasKeywordChar("|[]"));
    EXPECT_FALSE(failure::log::HasKeywordChar(""));
}

TEST(ExtractManifestKeywords, CollectsLiteralParts)
{
    // 只提取 <...> 之外的字面量，按 | 拆分并去除空白
    auto keywords = failure::log::ExtractManifestKeywords("<datetime>|UDMA_LOG_TAG|<function_name>[<line>]|<content>");
    ASSERT_EQ(keywords.size(), 1u);
    EXPECT_EQ(keywords[0], "UDMA_LOG_TAG");
}

TEST(ExtractManifestKeywords, SplitsAndDedups)
{
    // 同一段字面量中的重复关键字去重；纯标量字面量被丢弃
    auto keywords = failure::log::ExtractManifestKeywords(" foo | foo | <field> | | bar");
    ASSERT_EQ(keywords.size(), 2u);
    EXPECT_NE(std::find(keywords.begin(), keywords.end(), "foo"), keywords.end());
    EXPECT_NE(std::find(keywords.begin(), keywords.end(), "bar"), keywords.end());
}

TEST(ExtractManifestKeywords, IgnoresFieldContentAndUnclosed)
{
    // 范围字段 <type(a|b)> 内部的选项不作为关键字；未闭合的 < 截断后续提取
    auto keywords = failure::log::ExtractManifestKeywords("pre <type(a|b)> tail");
    ASSERT_EQ(keywords.size(), 2u);
    EXPECT_EQ(keywords[0], "pre");
    EXPECT_EQ(keywords[1], "tail");
}

TEST(BuildKeywordFilter, GrepFixedStrings)
{
    auto empty = failure::log::BuildKeywordFilter({});
    ASSERT_EQ(empty.size(), 2u);
    EXPECT_EQ(empty[0], "grep");
    EXPECT_EQ(empty[1], "-F");

    auto filter = failure::log::BuildKeywordFilter({"k1", "k2"});
    ASSERT_EQ(filter.size(), 6u);
    EXPECT_EQ(filter[2], "-e");
    EXPECT_EQ(filter[3], "k1");
    EXPECT_EQ(filter[4], "-e");
    EXPECT_EQ(filter[5], "k2");
}

TEST(WaitForChildren, EmptyListIsNoop)
{
    std::vector<pid_t> pids;
    failure::log::WaitForChildren(pids); // 不应崩溃
    SUCCEED();
}

TEST(SpawnPipeline, TwoStagePipelineProducesOutput)
{
    // echo -> grep 管道：能从返回的 FILE* 读回过滤结果
    std::vector<std::vector<std::string>> commands = {{"echo", "hello world"}, {"grep", "-F", "-e", "hello"}};
    std::vector<pid_t> pids;
    FILE *stream = failure::log::SpawnPipeline(commands, pids);
    ASSERT_NE(stream, nullptr);
    ASSERT_FALSE(pids.empty());
    char buf[256];
    ASSERT_NE(fgets(buf, sizeof(buf), stream), nullptr);
    EXPECT_STREQ(buf, "hello world\n");
    EXPECT_EQ(fgets(buf, sizeof(buf), stream), nullptr);
    fclose(stream);
    // 关闭输出流后回收子进程
    failure::log::WaitForChildren(pids);
    EXPECT_TRUE(pids.empty());
}

TEST(SpawnPipeline, MissingCommandReturnsNull)
{
    // 命令不存在：posix_spawnp 失败，返回 nullptr
    std::vector<std::vector<std::string>> commands = {{"witty_no_such_cmd_xyz"}};
    std::vector<pid_t> pids;
    FILE *stream = failure::log::SpawnPipeline(commands, pids);
    EXPECT_EQ(stream, nullptr);
}

// ---------------------------------------------------------------------------
// LogReader：USER 数据源（awk -F| 时间窗 + grep 关键字过滤）
// ---------------------------------------------------------------------------

TEST(LogReaderUserLog, ReadsSingleLineEvents)
{
    // 生成带关键字过滤的管道：只读出含 UMQ 的行
    TempDir dir;
    std::string path = dir.Write("user.log",
        "2024-01-15T10:30:01.123456+08:00|W|UMQ|first failure\n"
        "2024-01-15T10:30:02.123456+08:00|W|OTHER|no keyword\n"
        "2024-01-15T10:30:03.123456+08:00|W|UMQ|second failure\n");

    auto reader = MakeReader(failure::DataSourceOption::USER, path, SINGLE_MANIFEST);
    reader->CreateHandle();

    auto first = reader->ReadOnce();
    ASSERT_TRUE(first.has_value());
    EXPECT_EQ(first->attributes.at("content"), "first failure");
    EXPECT_EQ(first->pathCell.path, path);

    auto second = reader->ReadOnce();
    ASSERT_TRUE(second.has_value());
    EXPECT_EQ(second->attributes.at("content"), "second failure");

    EXPECT_FALSE(reader->ReadOnce().has_value());
}

TEST(LogReaderUserLog, MultilineEventMergesContinuationLines)
{
    // identifier 相同的续行合并为一条事件；不同 identifier 的行被缓存供下一次读取
    TempDir dir;
    std::string path = dir.Write("multi.log",
        "2024-01-15T10:30:01.123456+08:00|UMQ|sess1|line one\n"
        "2024-01-15T10:30:02.123456+08:00|UMQ|sess1|line two\n"
        "2024-01-15T10:30:03.123456+08:00|UMQ|sess2|other session");

    auto reader = MakeReader(failure::DataSourceOption::USER, path, MULTI_MANIFEST, true);
    reader->CreateHandle();

    auto first = reader->ReadOnce();
    ASSERT_TRUE(first.has_value());
    // 两条 sess1 行拼接（含换行），identifier 已从属性中删除
    EXPECT_EQ(first->text,
              "2024-01-15T10:30:01.123456+08:00|UMQ|sess1|line one\n"
              "2024-01-15T10:30:02.123456+08:00|UMQ|sess1|line two\n");
    EXPECT_EQ(first->attributes.find("identifier"), first->attributes.end());
    // content 属性只来自首行匹配，不含换行
    EXPECT_EQ(first->attributes.at("content"), "line one");

    // 缓存的 sess2 行成为下一条事件；awk print 会为无尾换行的末行补 \n
    auto second = reader->ReadOnce();
    ASSERT_TRUE(second.has_value());
    EXPECT_EQ(second->text, "2024-01-15T10:30:03.123456+08:00|UMQ|sess2|other session\n");

    EXPECT_FALSE(reader->ReadOnce().has_value());
}

TEST(LogReaderUserLog, LongLinesAndMissingTrailingNewline)
{
    // 超过 4096 缓冲的续行：触发 fgets 分块读取与容量扩充分支
    TempDir dir;
    const std::string longTail(5000, 'x');
    std::string path = dir.Write("long.log",
        "2024-01-15T10:30:01.123456+08:00|UMQ|sess|start\n"
        "2024-01-15T10:30:02.123456+08:00|UMQ|sess|" + longTail);

    auto reader = MakeReader(failure::DataSourceOption::USER, path, MULTI_MANIFEST, true);
    reader->CreateHandle();

    auto event = reader->ReadOnce();
    ASSERT_TRUE(event.has_value());
    // 首行带换行 + 超长续行；末行即使无尾换行，awk print 也会补 \n
    EXPECT_EQ(event->text,
              "2024-01-15T10:30:01.123456+08:00|UMQ|sess|start\n"
              "2024-01-15T10:30:02.123456+08:00|UMQ|sess|" + longTail + "\n");
    EXPECT_FALSE(reader->ReadOnce().has_value());
}

TEST(LogReaderUserLog, EmptyFileYieldsNoEvent)
{
    TempDir dir;
    std::string path = dir.Write("empty.log", "");

    auto reader = MakeReader(failure::DataSourceOption::USER, path, SINGLE_MANIFEST);
    reader->CreateHandle();
    EXPECT_FALSE(reader->ReadOnce().has_value());
}

TEST(LogReaderUserLog, InvalidDatetimeLineIsSkipped)
{
    // 模板命中但 datetime 无法解析的行：CreateEvent 失败后继续读取后续行
    TempDir dir;
    std::string path = dir.Write("bad.log",
        "not-a-date|W|UMQ|broken line\n"
        "2024-01-15T10:30:00|W|UMQ|good line\n");

    auto reader = MakeReader(failure::DataSourceOption::USER, path, SINGLE_MANIFEST);
    reader->CreateHandle();

    auto event = reader->ReadOnce();
    ASSERT_TRUE(event.has_value());
    EXPECT_EQ(event->attributes.at("content"), "good line");
    EXPECT_FALSE(reader->ReadOnce().has_value());
}

TEST(LogReaderUserLog, NoTemplateMatchYieldsNoEvent)
{
    TempDir dir;
    std::string path = dir.Write("nomatch.log", "2024-01-15T10:30:00|X|Y|Z\n");

    auto reader = MakeReader(failure::DataSourceOption::USER, path, SINGLE_MANIFEST);
    reader->CreateHandle();
    EXPECT_FALSE(reader->ReadOnce().has_value());
}

TEST(LogReaderUserLog, HandleLifecycleIsIdempotent)
{
    // CreateHandle/DestroyHandle 可重复调用；销毁后句柄重建可再次读取
    TempDir dir;
    std::string path = dir.Write("cycle.log", "2024-01-15T10:30:00|W|UMQ|only line\n");

    auto reader = MakeReader(failure::DataSourceOption::USER, path, SINGLE_MANIFEST);
    reader->CreateHandle();
    reader->CreateHandle();  // 已打开时不应重复打开
    ASSERT_TRUE(reader->ReadOnce().has_value());
    reader->DestroyHandle();
    reader->DestroyHandle(); // 未打开时为 no-op

    reader->CreateHandle();  // 重新打开，从头读取
    auto again = reader->ReadOnce();
    ASSERT_TRUE(again.has_value());
    EXPECT_EQ(again->attributes.at("content"), "only line");
}

TEST(LogReaderUserLog, RepeatedAddFailureModeKeepsWorking)
{
    // 重复添加同一故障模式：关键字去重后管道仍能正常产出事件
    TempDir dir;
    std::string path = dir.Write("dup.log", "2024-01-15T10:30:00|W|UMQ|dup line\n");

    failure::PathCell cell;
    cell.path = path;
    auto start = failure::DatetimeStrToTimestamp("2024-01-15T00:00:00");
    auto end = failure::DatetimeStrToTimestamp("2024-01-15T23:59:59");
    failure::log::LogReader reader(failure::DataSourceOption::USER, cell, *start, *end);
    failure::FailureMode mode;
    mode.component = "umq";
    mode.manifest = SINGLE_MANIFEST;
    mode.isMultiline = false;
    reader.AddFailureMode(mode);
    reader.AddFailureMode(mode);

    reader.CreateHandle();
    auto event = reader.ReadOnce();
    ASSERT_TRUE(event.has_value());
    EXPECT_EQ(event->attributes.at("content"), "dup line");
}

// ---------------------------------------------------------------------------
// LogReader：KERNEL 数据源（gawk 时间窗过滤）
// ---------------------------------------------------------------------------

TEST(LogReaderKernelLog, FiltersByTimeWindow)
{
    // 无括号行跳过；窗口前行跳过；窗口内行输出；窗口后行终止流
    TempDir dir;
    std::string path = dir.Write("kernel.log",
        "garbage line without bracket\n"
        "[Sun Jan 14 08:00:00 2024] umq: before window\n"
        "[Mon Jan 15 10:30:00 2024] umq: bind jetty success\n"
        "[Tue Jan 16 08:00:00 2024] umq: after window\n");

    auto reader = MakeReader(failure::DataSourceOption::KERNEL, path, KERNEL_MANIFEST);
    reader->CreateHandle();

    auto event = reader->ReadOnce();
    ASSERT_TRUE(event.has_value());
    // datetime 字段捕获含方括号的 syslog 时间戳
    auto expectedTs = failure::DatetimeStrToTimestamp("[Mon Jan 15 10:30:00 2024]");
    ASSERT_TRUE(expectedTs.has_value());
    EXPECT_EQ(event->timestamp, *expectedTs);
    EXPECT_EQ(event->attributes.at("content"), "bind jetty success");
    EXPECT_EQ(event->text, "[Mon Jan 15 10:30:00 2024] umq: bind jetty success\n");

    EXPECT_FALSE(reader->ReadOnce().has_value());
}

TEST(LogReaderKernelLog, CommandPathIsUsedWhenNotRegularFile)
{
    // 路径不是常规文件时被当作命令执行：echo -T 输出经 gawk 过滤后为空
    auto reader = MakeReader(failure::DataSourceOption::KERNEL, "echo", KERNEL_MANIFEST);
    reader->CreateHandle();
    EXPECT_FALSE(reader->ReadOnce().has_value());
}

TEST(LogReaderKernelLog, MissingFileHandleLifecycleIsSafe)
{
    // 文件不存在（路径也非可执行命令）：被当作命令 spawn 失败，句柄保持为空。
    // 此时 DestroyHandle/析构必须安全无崩溃；直接调用 ReadOnce 会因 fgets(空句柄) 段错误——
    // 生产缺陷（KERNEL 路径既非常规文件也非命令时必崩），已报告，勿修。
    TempDir dir;
    auto reader = MakeReader(failure::DataSourceOption::KERNEL, (dir.Path() / "no_such.log").string(),
                             KERNEL_MANIFEST);
    reader->CreateHandle();
    reader->DestroyHandle(); // 空句柄下应为无操作
    reader->DestroyHandle(); // 重复销毁同样安全
}
