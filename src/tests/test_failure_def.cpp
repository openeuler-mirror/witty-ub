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
#include "failure_def.h"
#include <json/json.h>
#include <string>
#include <vector>

TEST(EventTypeOptionFromString, ValidStrings) {
    EXPECT_EQ(failure::EventTypeOptionFromString("bind"), failure::EventTypeOption::BIND);
    EXPECT_EQ(failure::EventTypeOptionFromString("unbind"), failure::EventTypeOption::UNBIND);
    EXPECT_EQ(failure::EventTypeOptionFromString("post"), failure::EventTypeOption::POST);
}

TEST(EventTypeOptionFromString, InvalidString) {
    EXPECT_FALSE(failure::EventTypeOptionFromString("invalid").has_value());
    EXPECT_FALSE(failure::EventTypeOptionFromString("").has_value());
}

TEST(EventTypeOptionToString, AllOptions) {
    EXPECT_EQ(failure::EventTypeOptionToString(failure::EventTypeOption::BIND), "bind");
    EXPECT_EQ(failure::EventTypeOptionToString(failure::EventTypeOption::UNBIND), "unbind");
    EXPECT_EQ(failure::EventTypeOptionToString(failure::EventTypeOption::POST), "post");
    EXPECT_EQ(failure::EventTypeOptionToString(static_cast<failure::EventTypeOption>(99)), "unknown");
}

TEST(Split, BasicSplit) {
    std::vector<std::string> out;
    failure::Split(out, "a|b|c", '|');
    ASSERT_EQ(out.size(), 3u);
    EXPECT_EQ(out[0], "a");
    EXPECT_EQ(out[1], "b");
    EXPECT_EQ(out[2], "c");
}

TEST(Split, KeepEmpty) {
    std::vector<std::string> out;
    failure::Split(out, "a||c", '|', true);
    ASSERT_EQ(out.size(), 3u);
    EXPECT_EQ(out[1], "");
}

TEST(Split, NoKeepEmpty) {
    std::vector<std::string> out;
    failure::Split(out, "a||c", '|', false);
    ASSERT_EQ(out.size(), 2u);
}

TEST(DatetimeStrToTimestamp, Iso8601Format) {
    auto ts = failure::DatetimeStrToTimestamp("2024-01-15T10:30:00", true);
    ASSERT_TRUE(ts.has_value());
    EXPECT_GT(*ts, 0);
}

TEST(DatetimeStrToTimestamp, StandardFormat) {
    auto ts = failure::DatetimeStrToTimestamp("2024-01-15 10:30:00", true);
    ASSERT_TRUE(ts.has_value());
    EXPECT_GT(*ts, 0);
}

TEST(DatetimeStrToTimestamp, SyslogFormat) {
    auto ts = failure::DatetimeStrToTimestamp("[Mon Jan 15 10:30:00 2024]", true);
    ASSERT_TRUE(ts.has_value());
    EXPECT_GT(*ts, 0);
}

TEST(DatetimeStrToTimestamp, InvalidFormat) {
    EXPECT_FALSE(failure::DatetimeStrToTimestamp("invalid", true).has_value());
    EXPECT_FALSE(failure::DatetimeStrToTimestamp("", true).has_value());
}

TEST(DatetimeStrToTimestamp, WithMicroseconds) {
    auto ts = failure::DatetimeStrToTimestamp("2024-01-15T10:30:00.123456", true);
    ASSERT_TRUE(ts.has_value());
    EXPECT_GT(*ts, 0);
}

TEST(TimestampToDatetimeStr, StandardFormat) {
    auto ts = failure::DatetimeStrToTimestamp("2024-01-15T10:30:00", true);
    ASSERT_TRUE(ts.has_value());
    auto str = failure::TimestampToDatetimeStr(*ts, "standard");
    ASSERT_TRUE(str.has_value());
    EXPECT_EQ(*str, "2024-01-15 10:30:00");
}

TEST(TimestampToDatetimeStr, Iso8601Format) {
    auto ts = failure::DatetimeStrToTimestamp("2024-01-15T10:30:00", true);
    ASSERT_TRUE(ts.has_value());
    auto str = failure::TimestampToDatetimeStr(*ts, "iso8601");
    ASSERT_TRUE(str.has_value());
    EXPECT_EQ(*str, "2024-01-15T10:30:00");
}

TEST(FailureModeFromJson, HardwareComponent) {
    Json::Value j;
    j["component"] = "hardware";
    j["version"] = "1.0";
    j["is_multiline"] = false;
    j["manifest"] = "test manifest";
    j["log_path"] = "/var/log/test";
    auto mode = failure::FailureMode::FromJson(j);
    EXPECT_EQ(mode.component, "hardware");
    EXPECT_EQ(mode.version, "1.0");
    EXPECT_FALSE(mode.isMultiline);
    EXPECT_EQ(mode.dataSource.option, failure::DataSourceOption::KERNEL);
}

TEST(FailureModeFromJson, UserComponent) {
    Json::Value j;
    j["component"] = "umq";
    j["version"] = "2.0";
    j["is_multiline"] = true;
    j["manifest"] = "manifest";
    j["log_path"] = "/var/log/umq";
    auto mode = failure::FailureMode::FromJson(j);
    EXPECT_EQ(mode.component, "umq");
    EXPECT_EQ(mode.dataSource.option, failure::DataSourceOption::USER);
}

TEST(FailureEventQueryMatch, EmptyQueryMatchesAll) {
    failure::FailureMetadata md;
    md.eventType = failure::EventTypeOption::BIND;
    md.podId = "pod1";
    md.localEid = "eid1";
    md.localJettyId = "jetty1";
    failure::FailureEventQuery query;
    EXPECT_TRUE(query.Match(md, false));
}

TEST(FailureEventQueryMatch, EventTypeFilter) {
    failure::FailureMetadata md;
    md.eventType = failure::EventTypeOption::BIND;
    failure::FailureEventQuery query;
    query.eventTypes = {failure::EventTypeOption::POST};
    EXPECT_FALSE(query.Match(md, false));
    query.eventTypes = {failure::EventTypeOption::BIND};
    EXPECT_TRUE(query.Match(md, false));
}

TEST(FailureEventQueryMatch, PodIdFilter) {
    failure::FailureMetadata md;
    md.podId = "pod1";
    failure::FailureEventQuery query;
    query.podIds = {"pod2"};
    EXPECT_FALSE(query.Match(md, true));
    query.podIds = {"pod1"};
    EXPECT_TRUE(query.Match(md, true));
}

TEST(FailureEventQueryMatch, LocalEidFilter) {
    failure::FailureMetadata md;
    md.localEid = "eid1";
    failure::FailureEventQuery query;
    query.localEids = {"eid2"};
    EXPECT_FALSE(query.Match(md, false));
    query.localEids = {"eid1"};
    EXPECT_TRUE(query.Match(md, false));
}

TEST(FailureEventQueryMatch, JettyIdFilter) {
    failure::FailureMetadata md;
    md.localJettyId = "jetty1";
    failure::FailureEventQuery query;
    query.jettyIds = {"jetty2"};
    EXPECT_FALSE(query.Match(md, false));
    query.jettyIds = {"jetty1"};
    EXPECT_TRUE(query.Match(md, false));
}

TEST(FailureEventToJson, FullFields) {
    failure::FailureEvent event;
    event.timestamp = *failure::DatetimeStrToTimestamp("2024-01-15 10:30:00");
    event.component = "umq";
    event.pathCell.path = "/var/log/umq";
    event.text = "something failed";
    event.attributes["function_name"] = "umq_post";
    event.attributes["local_eid"] = "eid1";
    event.attributes["local_jetty_id"] = "jetty1";
    event.attributes["remote_eid"] = "eid2";
    event.attributes["remote_jetty_id"] = "jetty2";
    auto j = event.ToJson();
    EXPECT_TRUE(j.isObject());
    EXPECT_EQ(j["component"].asString(), "umq");
    EXPECT_EQ(j["path"].asString(), "/var/log/umq");
    EXPECT_EQ(j["text"].asString(), "something failed");
    EXPECT_EQ(j["attributes"]["function_name"].asString(), "umq_post");
    EXPECT_EQ(j["attributes"]["local_eid"].asString(), "eid1");
    EXPECT_EQ(j["attributes"]["local_jetty_id"].asString(), "jetty1");
    EXPECT_EQ(j["attributes"]["remote_eid"].asString(), "eid2");
    EXPECT_EQ(j["attributes"]["remote_jetty_id"].asString(), "jetty2");
    // 无关属性不输出
    EXPECT_FALSE(j["attributes"].isMember("other"));
}

TEST(FailureEventToJson, EmptyAttributes) {
    failure::FailureEvent event;
    event.timestamp = 0;
    event.component = "ubsocket";
    auto j = event.ToJson();
    EXPECT_TRUE(j["attributes"].isObject());
    EXPECT_EQ(j["attributes"].size(), 0u);
    EXPECT_TRUE(j.isMember("time"));
}

TEST(FailureMetadataToJson, FullFields) {
    failure::FailureMetadata md;
    md.eventType = failure::EventTypeOption::POST;
    md.podId = "pod1";
    md.programName = "prog";
    md.procId = "42";
    md.threadId = "43";
    md.timestamp = *failure::DatetimeStrToTimestamp("2024-01-15 10:30:00");
    md.localEid = "eid1";
    md.localJettyId = "jetty1";
    md.remoteEid = "eid2";
    md.remoteJettyId = "jetty2";
    md.text = "meta text";
    md.role = "tx";

    failure::FailureEvent event;
    event.timestamp = md.timestamp;
    event.component = "umq";
    event.text = "event text";
    md.events = {&event, nullptr};

    auto j = md.ToJson();
    EXPECT_EQ(j["event_type"].asString(), "post");
    EXPECT_EQ(j["pod_id"].asString(), "pod1");
    EXPECT_EQ(j["program_name"].asString(), "prog");
    EXPECT_EQ(j["proc_id"].asString(), "42");
    EXPECT_EQ(j["thread_id"].asString(), "43");
    EXPECT_EQ(j["local_eid"].asString(), "eid1");
    EXPECT_EQ(j["local_jetty_id"].asString(), "jetty1");
    EXPECT_EQ(j["remote_eid"].asString(), "eid2");
    EXPECT_EQ(j["remote_jetty_id"].asString(), "jetty2");
    EXPECT_EQ(j["text"].asString(), "meta text");
    EXPECT_EQ(j["role"].asString(), "tx");
    // events 数组：nullptr 被跳过，仅保留 1 条
    ASSERT_EQ(j["logs"].size(), 1u);
    EXPECT_EQ(j["logs"][0]["text"].asString(), "event text");
}

TEST(FailureMetadataToJson, OptionalNulls) {
    failure::FailureMetadata md;
    md.eventType = failure::EventTypeOption::BIND;
    md.programName = "prog";
    md.procId = "1";
    md.threadId = "2";
    md.localEid = "eid";
    md.localJettyId = "jetty";
    auto j = md.ToJson();
    EXPECT_TRUE(j["pod_id"].isNull());
    EXPECT_TRUE(j["remote_eid"].isNull());
    EXPECT_TRUE(j["remote_jetty_id"].isNull());
    EXPECT_TRUE(j["role"].isNull());
    EXPECT_EQ(j["logs"].size(), 0u);
}

TEST(DatetimeStrToTimestamp, TabSeparatorRejected) {
    // strptime 的 %d %H 中空格可匹配任意空白，但实现要求第 10 位必须是字面空格
    EXPECT_FALSE(failure::DatetimeStrToTimestamp("2024-01-15\t10:30:00").has_value());
}

TEST(DatetimeStrToTimestamp, NonexistentDateRejected) {
    // 2 月 30 日会被 mktime 规范化为 3 月 1 日，与原始字段不一致
    EXPECT_FALSE(failure::DatetimeStrToTimestamp("2024-02-30 10:00:00").has_value());
}

TEST(DatetimeStrToTimestamp, PreEpochRejected) {
    // 东八区下 1970-01-01 之前的时间戳为负值，被拒绝
    EXPECT_FALSE(failure::DatetimeStrToTimestamp("1969-01-01 00:00:00").has_value());
}

TEST(DatetimeStrToTimestamp, FutureRejectedUnlessAllowed) {
    EXPECT_FALSE(failure::DatetimeStrToTimestamp("2999-01-01 00:00:00").has_value());
    EXPECT_TRUE(failure::DatetimeStrToTimestamp("2999-01-01 00:00:00", true).has_value());
}

TEST(DatetimeStrToTimestamp, YearOverflowRejected) {
    // 年份超出 time_t 表示范围，mktime 返回 -1
    EXPECT_FALSE(failure::DatetimeStrToTimestamp("99999999999999-01-01 00:00:00").has_value());
}

TEST(DatetimeStrToTimestamp, MicrosecondPaddingAndTruncation) {
    auto base = failure::DatetimeStrToTimestamp("2024-01-15T10:30:00");
    ASSERT_TRUE(base.has_value());
    // ".12" 补零为 120000 微秒
    auto shortFrac = failure::DatetimeStrToTimestamp("2024-01-15T10:30:00.12");
    ASSERT_TRUE(shortFrac.has_value());
    EXPECT_EQ(*shortFrac - *base, 120000);
    // 超过 6 位截断为前 6 位
    auto longFrac = failure::DatetimeStrToTimestamp("2024-01-15T10:30:00.123456789");
    ASSERT_TRUE(longFrac.has_value());
    EXPECT_EQ(*longFrac - *base, 123456);
}

TEST(TimestampToDatetimeStr, SyslogFormat) {
    auto str = failure::TimestampToDatetimeStr(0, "syslog");
    ASSERT_TRUE(str.has_value());
    // 格式为 "[Thu Jan 01 08:00:00 1970]"（东八区），校验首尾括号与年份
    EXPECT_EQ(str->front(), '[');
    EXPECT_EQ(str->back(), ']');
    EXPECT_NE(str->find("1970"), std::string::npos);
}

TEST(TimestampToDatetimeStr, UnknownFormatReturnsNullopt) {
    EXPECT_FALSE(failure::TimestampToDatetimeStr(0, "bogus").has_value());
}
