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

#include <string>
#include <vector>

#include "log_template.h"
#include "logger.h"

// 被测实现中打日志（LOG_WARN/LOG_ERROR 路径），log4cplus 必须先初始化，否则崩溃。
struct LoggerInit {
    LoggerInit() { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

namespace failure::log {
// log_template.cpp 中的内部自由函数（外部链接），直接前向声明进行直测
std::string EscapeRegex(const std::string &str);
bool AppendRangeGroup(const std::string &fieldExpr, std::vector<std::string> &fields, std::string &patternStr);
} // namespace failure::log

namespace {

// 构造一个最小可用的故障模式
failure::FailureMode MakeMode(const std::string &manifest, bool multiline = false)
{
    failure::FailureMode mode;
    mode.component = "umq";
    mode.version = "1.0";
    mode.isMultiline = multiline;
    mode.manifest = manifest;
    return mode;
}

} // namespace

// ---------------------------------------------------------------------------
// EscapeRegex：re2::QuoteMeta 包装
// ---------------------------------------------------------------------------

TEST(EscapeRegex, PlainTextUnchanged)
{
    // 普通字符不需要转义
    EXPECT_EQ(failure::log::EscapeRegex("abc123"), "abc123");
    EXPECT_EQ(failure::log::EscapeRegex(""), "");
}

TEST(EscapeRegex, EscapesMetacharacters)
{
    // 正则元字符必须被转义，否则会被当作模式语义
    EXPECT_EQ(failure::log::EscapeRegex("a.b"), "a\\.b");
    EXPECT_EQ(failure::log::EscapeRegex("a|b"), "a\\|b");
    EXPECT_EQ(failure::log::EscapeRegex("u(x)"), "u\\(x\\)");
}

// ---------------------------------------------------------------------------
// AppendRangeGroup：字段表达式 -> 捕获组
// ---------------------------------------------------------------------------

TEST(AppendRangeGroup, PlainFieldBecomesDotStarGroup)
{
    // 无范围括号：字段名入 fields，模式追加 (.*)
    std::vector<std::string> fields;
    std::string pattern;
    ASSERT_TRUE(failure::log::AppendRangeGroup("datetime", fields, pattern));
    ASSERT_EQ(fields.size(), 1u);
    EXPECT_EQ(fields[0], "datetime");
    EXPECT_EQ(pattern, "(.*)");
}

TEST(AppendRangeGroup, RangeOptionsBecomeAlternation)
{
    // <log_type(UMQ_AE/UMQ_API)>：范围选项按 | 拼为捕获组
    std::vector<std::string> fields;
    std::string pattern;
    ASSERT_TRUE(failure::log::AppendRangeGroup("log_type(UMQ_AE/UMQ_API)", fields, pattern));
    ASSERT_EQ(fields.size(), 1u);
    EXPECT_EQ(fields[0], "log_type");
    EXPECT_EQ(pattern, "(UMQ_AE|UMQ_API)");
}

TEST(AppendRangeGroup, RangeOptionsAreEscaped)
{
    // 范围选项中的正则元字符需要转义
    std::vector<std::string> fields;
    std::string pattern;
    ASSERT_TRUE(failure::log::AppendRangeGroup("type(a.b/c)", fields, pattern));
    EXPECT_EQ(pattern, "(a\\.b|c)");
}

TEST(AppendRangeGroup, RangeWithEmptyOption)
{
    // 空选项只跳过转义，分隔符仍保留
    std::vector<std::string> fields;
    std::string pattern;
    ASSERT_TRUE(failure::log::AppendRangeGroup("x(a/)", fields, pattern));
    EXPECT_EQ(pattern, "(a|)");

    // 空范围 "()" 生成空捕获组
    std::vector<std::string> fields2;
    std::string pattern2;
    ASSERT_TRUE(failure::log::AppendRangeGroup("x()", fields2, pattern2));
    EXPECT_EQ(pattern2, "()");
}

TEST(AppendRangeGroup, UnclosedRangeFails)
{
    // 缺少 ')'：返回 false（内部打 LOG_WARN）
    std::vector<std::string> fields;
    std::string pattern;
    EXPECT_FALSE(failure::log::AppendRangeGroup("type(a", fields, pattern));
    EXPECT_TRUE(fields.empty());
    EXPECT_TRUE(pattern.empty());
}

// ---------------------------------------------------------------------------
// LogTemplate::Match：manifest 编译 + 行捕获
// ---------------------------------------------------------------------------

TEST(LogTemplateMatch, CapturesAllFields)
{
    // 基本三字段 manifest
    failure::log::LogTemplate tmpl(MakeMode("<datetime> ubase <id>: <content>"));
    auto attrs = tmpl.Match("2024-01-15 10:30:00.123 ubase 42: hello world");
    ASSERT_TRUE(attrs.has_value());
    EXPECT_EQ((*attrs)["datetime"], "2024-01-15 10:30:00.123");
    EXPECT_EQ((*attrs)["id"], "42");
    EXPECT_EQ((*attrs)["content"], "hello world");
}

TEST(LogTemplateMatch, RangeFieldAcceptsListedOptionOnly)
{
    failure::log::LogTemplate tmpl(MakeMode("|<log_type(UMQ_AE/UMQ_API)>|rest"));
    auto hit = tmpl.Match("|UMQ_API|rest");
    ASSERT_TRUE(hit.has_value());
    EXPECT_EQ((*hit)["log_type"], "UMQ_API");

    // 范围之外的选项不匹配
    EXPECT_FALSE(tmpl.Match("|UMQ_CQE|rest").has_value());
}

TEST(LogTemplateMatch, EmptyFieldMatchesWithoutCapturing)
{
    // <> 生成不捕获的 .*，且不进入字段表
    failure::log::LogTemplate tmpl(MakeMode("<datetime> {<identifier>}[Hardware Error]: <>"));
    auto attrs = tmpl.Match("2024-01-15 10:30:00 {abc}[Hardware Error]: xyz");
    ASSERT_TRUE(attrs.has_value());
    EXPECT_EQ(attrs->size(), 2u);
    EXPECT_EQ((*attrs)["datetime"], "2024-01-15 10:30:00");
    EXPECT_EQ((*attrs)["identifier"], "abc");
}

TEST(LogTemplateMatch, UnclosedFieldStopsPatternBuild)
{
    // 未闭合的 < > ：截断后续字面量，但已生成的模式仍可用（这里可匹配前缀）
    failure::log::LogTemplate tmpl(MakeMode("foo <bar"));
    auto attrs = tmpl.Match("foo <bar");
    // 模式仅包含已转义前缀 "foo "，能匹配，且无捕获字段
    ASSERT_TRUE(attrs.has_value());
    EXPECT_TRUE(attrs->empty());
}

TEST(LogTemplateMatch, NonMatchingLineReturnsNullopt)
{
    failure::log::LogTemplate tmpl(MakeMode("prefix <content>"));
    EXPECT_FALSE(tmpl.Match("totally different line").has_value());
    EXPECT_FALSE(tmpl.Match("").has_value());
}

TEST(LogTemplateMatch, UnanchoredMatchInsideLine)
{
    // UNANCHORED：模式可在行内任意位置命中；普通字段捕获 (.*) 到行尾，故字段后不应再有内容
    failure::log::LogTemplate tmpl(MakeMode("ERROR <code>"));
    auto attrs = tmpl.Match("2024-01-15 10:30:00 [x] ERROR 1234");
    ASSERT_TRUE(attrs.has_value());
    EXPECT_EQ((*attrs)["code"], "1234");
}

// ---------------------------------------------------------------------------
// LogTemplate::CreateEvent：属性 + 原始行 -> FailureEvent
// ---------------------------------------------------------------------------

TEST(LogTemplateCreateEvent, MissingDatetimeReturnsNullopt)
{
    failure::log::LogTemplate tmpl(MakeMode("<id>"));
    std::unordered_map<std::string, std::string> attrs;
    attrs["id"] = "42";
    EXPECT_FALSE(tmpl.CreateEvent(std::move(attrs), "line").has_value());
}

TEST(LogTemplateCreateEvent, InvalidDatetimeReturnsNullopt)
{
    failure::log::LogTemplate tmpl(MakeMode("<datetime>"));
    std::unordered_map<std::string, std::string> attrs;
    attrs["datetime"] = "not a datetime";
    EXPECT_FALSE(tmpl.CreateEvent(std::move(attrs), "line").has_value());

    // 未来时间默认不允许
    std::unordered_map<std::string, std::string> future;
    future["datetime"] = "2999-01-01T00:00:00";
    EXPECT_FALSE(tmpl.CreateEvent(std::move(future), "line").has_value());
}

TEST(LogTemplateCreateEvent, ValidAttributesProduceEvent)
{
    failure::log::LogTemplate tmpl(MakeMode("<datetime> ubase <id>: <content>"));
    std::unordered_map<std::string, std::string> attrs;
    attrs["datetime"] = "2024-01-15T10:30:00";
    attrs["id"] = "42";
    auto event = tmpl.CreateEvent(std::move(attrs), "raw log line");
    ASSERT_TRUE(event.has_value());
    // 时间戳为微秒精度
    auto expectedTs = failure::DatetimeStrToTimestamp("2024-01-15T10:30:00");
    ASSERT_TRUE(expectedTs.has_value());
    EXPECT_EQ(event->timestamp, *expectedTs);
    EXPECT_EQ(event->component, "umq");
    EXPECT_EQ(event->text, "raw log line");
    EXPECT_EQ(event->attributes.at("id"), "42");
    // 属性被移动进事件
    EXPECT_EQ(event->attributes.at("datetime"), "2024-01-15T10:30:00");
}
