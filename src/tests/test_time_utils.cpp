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
#include "time_utils.h"

TEST(ParseFixedInt, ValidInput) {
    int result = 0;
    EXPECT_TRUE(brpc::time::ParseFixedInt("20240115", 0, 4, result));
    EXPECT_EQ(result, 2024);
}
TEST(ParseFixedInt, ValidMonth) {
    int result = 0;
    EXPECT_TRUE(brpc::time::ParseFixedInt("20240115", 4, 2, result));
    EXPECT_EQ(result, 1);
}
TEST(ParseFixedInt, OutOfBounds) {
    int result = 0;
    EXPECT_FALSE(brpc::time::ParseFixedInt("123", 1, 5, result));
}
TEST(ParseFixedInt, NonDigit) {
    int result = 0;
    EXPECT_FALSE(brpc::time::ParseFixedInt("20a4", 0, 4, result));
}

TEST(BuildUtc8Timestamp, ValidTimestamp) {
    brpc::time::CivilTime ct{};
    ct.year = 2024;
    ct.month = 1;
    ct.day = 15;
    ct.hour = 10;
    ct.minute = 30;
    ct.second = 0;
    ct.microsecond = 0;
    std::int64_t ts = 0;
    EXPECT_TRUE(brpc::time::BuildUtc8Timestamp(ct, ts));
    // 2024-01-15 10:30:00 UTC+8 = 2024-01-15 02:30:00 UTC
    // = (days_since_epoch * 86400 + 2*3600 + 30*60 - 8*3600) * 1000000
    EXPECT_GT(ts, 0);
}
TEST(BuildUtc8Timestamp, LeapYearFeb29) {
    brpc::time::CivilTime ct{};
    ct.year = 2024;
    ct.month = 2;
    ct.day = 29;
    ct.hour = 0;
    ct.minute = 0;
    ct.second = 0;
    ct.microsecond = 0;
    std::int64_t ts = 0;
    EXPECT_TRUE(brpc::time::BuildUtc8Timestamp(ct, ts));
}
TEST(BuildUtc8Timestamp, NonLeapYearFeb29) {
    brpc::time::CivilTime ct{};
    ct.year = 2023;
    ct.month = 2;
    ct.day = 29;
    ct.hour = 0;
    ct.minute = 0;
    ct.second = 0;
    ct.microsecond = 0;
    std::int64_t ts = 0;
    EXPECT_FALSE(brpc::time::BuildUtc8Timestamp(ct, ts));
}
TEST(BuildUtc8Timestamp, InvalidMonth) {
    brpc::time::CivilTime ct{};
    ct.year = 2024;
    ct.month = 13;
    ct.day = 1;
    ct.hour = 0;
    ct.minute = 0;
    ct.second = 0;
    ct.microsecond = 0;
    std::int64_t ts = 0;
    EXPECT_FALSE(brpc::time::BuildUtc8Timestamp(ct, ts));
}
TEST(BuildUtc8Timestamp, InvalidHour) {
    brpc::time::CivilTime ct{};
    ct.year = 2024;
    ct.month = 1;
    ct.day = 1;
    ct.hour = 24;
    ct.minute = 0;
    ct.second = 0;
    ct.microsecond = 0;
    std::int64_t ts = 0;
    EXPECT_FALSE(brpc::time::BuildUtc8Timestamp(ct, ts));
}
TEST(BuildUtc8Timestamp, InvalidMicrosecond) {
    brpc::time::CivilTime ct{};
    ct.year = 2024;
    ct.month = 1;
    ct.day = 1;
    ct.hour = 0;
    ct.minute = 0;
    ct.second = 0;
    ct.microsecond = 1000000;
    std::int64_t ts = 0;
    EXPECT_FALSE(brpc::time::BuildUtc8Timestamp(ct, ts));
}
