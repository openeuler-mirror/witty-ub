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
#include "failure_log_helper.h"
#include <string>
#include <vector>

// Test WildcardMatch
TEST(WildcardMatch, StarMatchesAnything) {
    EXPECT_TRUE(diag::log_helper::WildcardMatch("*", "/path/to/file.txt"));
    EXPECT_TRUE(diag::log_helper::WildcardMatch("/path/*", "/path/to/file.txt"));
}
TEST(WildcardMatch, QuestionMarkMatchesSingleChar) {
    EXPECT_TRUE(diag::log_helper::WildcardMatch("?.txt", "a.txt"));
    EXPECT_FALSE(diag::log_helper::WildcardMatch("?.txt", "ab.txt"));
}
TEST(WildcardMatch, NoWildcardExactMatch) {
    EXPECT_TRUE(diag::log_helper::WildcardMatch("/exact/path", "/exact/path"));
    EXPECT_FALSE(diag::log_helper::WildcardMatch("/exact/path", "/other/path"));
}

// Test SplitView
TEST(SplitView, BasicSplit) {
    std::vector<std::string_view> out;
    diag::log_helper::SplitView(out, "a|b|c", "|");
    ASSERT_EQ(out.size(), 3u);
    EXPECT_EQ(out[0], "a");
    EXPECT_EQ(out[1], "b");
    EXPECT_EQ(out[2], "c");
}
TEST(SplitView, KeepEmpty) {
    std::vector<std::string_view> out;
    diag::log_helper::SplitView(out, "a||c", "|", true);
    ASSERT_EQ(out.size(), 3u);
    EXPECT_EQ(out[1], "");
}
TEST(SplitView, NoKeepEmpty) {
    std::vector<std::string_view> out;
    diag::log_helper::SplitView(out, "a||c", "|", false);
    ASSERT_EQ(out.size(), 2u);
}
TEST(SplitView, EmptyDelim) {
    std::vector<std::string_view> out;
    diag::log_helper::SplitView(out, "hello", "");
    ASSERT_EQ(out.size(), 1u);
    EXPECT_EQ(out[0], "hello");
}
TEST(SplitView, EmptyString) {
    std::vector<std::string_view> out;
    diag::log_helper::SplitView(out, "", "|");
    EXPECT_TRUE(out.empty());
}

// Test IsDigit
TEST(IsDigit, Digits) {
    EXPECT_TRUE(diag::log_helper::IsDigit('0'));
    EXPECT_TRUE(diag::log_helper::IsDigit('9'));
    EXPECT_FALSE(diag::log_helper::IsDigit('a'));
    EXPECT_FALSE(diag::log_helper::IsDigit('/'));
}

// Test IsTimestampTAt
TEST(IsTimestampTAt, ValidTimestamp) {
    EXPECT_TRUE(diag::log_helper::IsTimestampTAt("2024-01-15T10:30:00", 0));
}
TEST(IsTimestampTAt, InvalidPosition) {
    EXPECT_FALSE(diag::log_helper::IsTimestampTAt("hello world", 0));
}
TEST(IsTimestampTAt, OutOfBounds) {
    EXPECT_FALSE(diag::log_helper::IsTimestampTAt("short", 0));
}

// Test FindTimestampT
TEST(FindTimestampT, ValidLine) {
    auto result = diag::log_helper::FindTimestampT("log 2024-01-15T10:30:00 message");
    EXPECT_FALSE(result.empty());
    EXPECT_EQ(result, "2024-01-15T10:30:00");
}
TEST(FindTimestampT, NoTimestamp) {
    auto result = diag::log_helper::FindTimestampT("no timestamp here");
    EXPECT_TRUE(result.empty());
}

// Test ToTimestampTBound
TEST(ToTimestampTBound, ReplacesSpaceWithT) {
    EXPECT_EQ(diag::log_helper::ToTimestampTBound("2024-01-15 10:30:00"), "2024-01-15T10:30:00");
}
TEST(ToTimestampTBound, AlreadyHasT) {
    EXPECT_EQ(diag::log_helper::ToTimestampTBound("2024-01-15T10:30:00"), "2024-01-15T10:30:00");
}

// Test TrimView
TEST(TrimView, StripsBothSides) {
    EXPECT_EQ(diag::log_helper::TrimView("  hello  "), "hello");
    EXPECT_EQ(diag::log_helper::TrimView("hello"), "hello");
    EXPECT_EQ(diag::log_helper::TrimView("   "), "");
}

// Test ParseInt
TEST(ParseInt, ValidInt) {
    int val = 0;
    EXPECT_TRUE(diag::log_helper::ParseInt("123", val));
    EXPECT_EQ(val, 123);
}
TEST(ParseInt, WithSpaces) {
    int val = 0;
    EXPECT_TRUE(diag::log_helper::ParseInt("  456  ", val));
    EXPECT_EQ(val, 456);
}
TEST(ParseInt, Invalid) {
    int val = 0;
    EXPECT_FALSE(diag::log_helper::ParseInt("abc", val));
    EXPECT_FALSE(diag::log_helper::ParseInt("", val));
}

// Test ToStringFields
TEST(ToStringFields, ConvertsViews) {
    std::vector<std::string_view> views = {"a", "b", "c"};
    auto result = diag::log_helper::ToStringFields(views);
    ASSERT_EQ(result.size(), 3u);
    EXPECT_EQ(result[0], "a");
    EXPECT_EQ(result[1], "b");
    EXPECT_EQ(result[2], "c");
}

// Test Trim
TEST(Trim, StripsBothSides) {
    EXPECT_EQ(diag::log_helper::Trim("  hello  "), "hello");
    EXPECT_EQ(diag::log_helper::Trim("hello"), "hello");
    EXPECT_EQ(diag::log_helper::Trim(""), "");
}
