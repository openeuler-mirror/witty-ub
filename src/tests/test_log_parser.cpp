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

#include "log_parser.h"
#include "logger.h"

// 解析器内部构造 LogTemplate 时可能触发日志路径，log4cplus 必须先初始化
struct LoggerInit {
    LoggerInit() noexcept { rack::logger::init(nullptr); }
};
static LoggerInit g_loggerInit;

namespace {

// 构造故障模式：manifest 决定匹配形状，isMultiline 决定归类
failure::FailureMode MakeMode(const std::string &manifest, bool multiline)
{
    failure::FailureMode mode;
    mode.component = "umq";
    mode.version = "1.0";
    mode.isMultiline = multiline;
    mode.manifest = manifest;
    return mode;
}

} // namespace

TEST(LogParser, EmptyParserMatchesNothing)
{
    // 未添加任何故障模式时，两个匹配接口均返回空
    failure::log::LogParser parser;
    EXPECT_FALSE(parser.MatchSingleLineTemplate("any line").has_value());
    EXPECT_FALSE(parser.MatchMultiLineTemplate("any line").has_value());
}

TEST(LogParser, AddFailureModeClassifiesMultiline)
{
    // isMultiline=true 的模式只进入多行模板表
    failure::log::LogParser parser;
    parser.AddFailureMode(MakeMode("<datetime>|UMQ|<identifier>|<content>", true));

    auto multi = parser.MatchMultiLineTemplate("2024-01-15T10:30:00|UMQ|sess1|first");
    ASSERT_TRUE(multi.has_value());
    EXPECT_EQ(multi->second["identifier"], "sess1");
    // 单行模板表中没有该模式
    EXPECT_FALSE(parser.MatchSingleLineTemplate("2024-01-15T10:30:00|UMQ|sess1|first").has_value());
}

TEST(LogParser, AddFailureModeClassifiesSingleLine)
{
    // isMultiline=false 的模式只进入单行模板表
    failure::log::LogParser parser;
    parser.AddFailureMode(MakeMode("<datetime> ubase <id>: <content>", false));

    auto single = parser.MatchSingleLineTemplate("2024-01-15 10:30:00 ubase 7: boom");
    ASSERT_TRUE(single.has_value());
    EXPECT_EQ(single->second["id"], "7");
    // 多行模板表中没有该模式
    EXPECT_FALSE(parser.MatchMultiLineTemplate("2024-01-15 10:30:00 ubase 7: boom").has_value());
}

TEST(LogParser, FirstMatchingTemplateWins)
{
    // 两个单行模板都能匹配同一行时，返回先添加的那个
    failure::log::LogParser parser;
    parser.AddFailureMode(MakeMode("prefix <v1>", false));
    parser.AddFailureMode(MakeMode("prefix <v2>", false));

    auto entry = parser.MatchSingleLineTemplate("prefix payload");
    ASSERT_TRUE(entry.has_value());
    // 通过捕获字段名区分命中的模板
    ASSERT_EQ(entry->second.size(), 1u);
    EXPECT_NE(entry->second.find("v1"), entry->second.end());
}

TEST(LogParser, MultiLineFirstMatchingTemplateWins)
{
    // 多行模板表同样遵循先添加者优先
    failure::log::LogParser parser;
    parser.AddFailureMode(MakeMode("<m1>", true));
    parser.AddFailureMode(MakeMode("<m2>", true));

    auto entry = parser.MatchMultiLineTemplate("some text");
    ASSERT_TRUE(entry.has_value());
    EXPECT_NE(entry->second.find("m1"), entry->second.end());
}

TEST(LogParser, MixedModesMatchedIndependently)
{
    // 混合添加：多行/单行各自独立匹配
    failure::log::LogParser parser;
    parser.AddFailureMode(MakeMode("<datetime>|UMQ|<identifier>|<content>", true));
    parser.AddFailureMode(MakeMode("<datetime> ubase <id>: <content>", false));

    auto single = parser.MatchSingleLineTemplate("2024-01-15 10:30:00 ubase 9: crash");
    ASSERT_TRUE(single.has_value());
    EXPECT_EQ(single->second["id"], "9");

    auto multi = parser.MatchMultiLineTemplate("2024-01-15T10:30:00|UMQ|s|c");
    ASSERT_TRUE(multi.has_value());
    EXPECT_EQ(multi->second["identifier"], "s");

    // 单行模板的行不会误命中多行模板，反之亦然
    EXPECT_FALSE(parser.MatchMultiLineTemplate("2024-01-15 10:30:00 ubase 9: crash").has_value());
    EXPECT_FALSE(parser.MatchSingleLineTemplate("2024-01-15T10:30:00|UMQ|s|c").has_value());
}

TEST(LogParser, NonMatchingLineSkipsAllTemplates)
{
    // 行不匹配任何已注册模板时返回空
    failure::log::LogParser parser;
    parser.AddFailureMode(MakeMode("alpha <v>", false));
    parser.AddFailureMode(MakeMode("beta <v>", false));
    EXPECT_FALSE(parser.MatchSingleLineTemplate("gamma something").has_value());
}

TEST(LogParser, TemplateEntryCarriesAttributes)
{
    // TemplateEntry 携带命中的模板指针与属性映射
    failure::log::LogParser parser;
    parser.AddFailureMode(MakeMode("<datetime>|W|<content>", false));

    auto entry = parser.MatchSingleLineTemplate("2024-01-15T10:30:00|W|warning text");
    ASSERT_TRUE(entry.has_value());
    ASSERT_NE(entry->first, nullptr);
    EXPECT_EQ(entry->second["datetime"], "2024-01-15T10:30:00");
    EXPECT_EQ(entry->second["content"], "warning text");
}
