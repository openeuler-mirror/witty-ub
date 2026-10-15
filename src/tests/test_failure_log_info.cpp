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
#include "failure_log_info.h"
#include "failure_def.h"

TEST(LevelOptionFromString, ValidLevels) {
    EXPECT_EQ(diag::LevelOptionFromString("I"), diag::LevelOption::INFO);
    EXPECT_EQ(diag::LevelOptionFromString("W"), diag::LevelOption::WARN);
    EXPECT_EQ(diag::LevelOptionFromString("D"), diag::LevelOption::DEBUG);
    EXPECT_EQ(diag::LevelOptionFromString("E"), diag::LevelOption::ERROR);
    EXPECT_EQ(diag::LevelOptionFromString("F"), diag::LevelOption::FATAL);
}
TEST(LevelOptionFromString, InvalidLevel) {
    EXPECT_FALSE(diag::LevelOptionFromString("X").has_value());
    EXPECT_FALSE(diag::LevelOptionFromString("").has_value());
}

TEST(FailureLogInfo, ConstructionRuntime) {
    std::vector<std::string> fields(8);
    fields[0] = "2024-01-15 10:30:00";
    fields[1] = "I";
    fields[2] = "file.cpp:42";
    fields[3] = "pod1";
    fields[4] = "123:456";
    fields[5] = "trace1";
    fields[6] = "cluster1";
    fields[7] = "test message";
    diag::FailureLogInfoRuntime info(fields, "raw log line");
    auto expectedTs = failure::DatetimeStrToTimestamp("2024-01-15 10:30:00");
    ASSERT_TRUE(expectedTs.has_value());
    EXPECT_EQ(info.timestamp, *expectedTs);
    EXPECT_EQ(info.level, diag::LevelOption::INFO);
    EXPECT_EQ(info.podName, "pod1");
    EXPECT_EQ(info.pid, 123);
    EXPECT_EQ(info.tid, 456);
    EXPECT_EQ(info.traceId, "trace1");
    EXPECT_EQ(info.clusterName, "cluster1");
    EXPECT_EQ(info.message, "test message");
    EXPECT_EQ(info.rawLog, "raw log line");
}

TEST(FailureLogInfo, ConstructionAccess) {
    std::vector<std::string> fields(13);
    fields[0] = "2024-01-15 10:30:00";
    fields[1] = "I";
    fields[2] = "file.cpp:42";
    fields[3] = "pod1";
    fields[4] = "123:456";
    fields[5] = "trace1";
    fields[6] = "cluster1";
    fields[7] = "200";
    fields[8] = "GET";
    fields[9] = "100";
    fields[10] = "1024";
    fields[11] = "req msg";
    fields[12] = "resp msg";
    diag::FailureLogInfoAccess info(fields, "raw log");
    EXPECT_EQ(info.level, diag::LevelOption::INFO);
    EXPECT_EQ(info.statusCode, 200);
    EXPECT_EQ(info.action, "GET");
    EXPECT_EQ(info.cost, 100);
    EXPECT_EQ(info.dataSize, 1024);
    EXPECT_EQ(info.reqMsg, "req msg");
    EXPECT_EQ(info.respMsg, "resp msg");
}

TEST(FailureLogInfo, InsufficientFieldsThrows) {
    std::vector<std::string> fields(5);
    EXPECT_THROW(diag::FailureLogInfoRuntime info(fields, ""), std::runtime_error);
}

TEST(FailureLogInfo, InvalidLevelThrows) {
    std::vector<std::string> fields(8);
    fields[0] = "2024-01-15 10:30:00";
    fields[1] = "X";
    fields[2] = "file.cpp:42";
    fields[3] = "pod1";
    fields[4] = "123:456";
    fields[5] = "trace1";
    fields[6] = "cluster1";
    fields[7] = "msg";
    EXPECT_THROW(diag::FailureLogInfoRuntime info(fields, ""), std::runtime_error);
}

TEST(FailureLogInfo, BindFailureMode) {
    std::vector<std::string> fields(8);
    fields[0] = "2024-01-15 10:30:00";
    fields[1] = "I";
    fields[2] = "file.cpp:42";
    fields[3] = "pod1";
    fields[4] = "123:456";
    fields[5] = "trace1";
    fields[6] = "cluster1";
    fields[7] = "msg";
    diag::FailureLogInfoRuntime info(fields, "raw");
    info.BindFailureMode("FM001");
    info.BindFailureMode("FM002");
    ASSERT_EQ(info.failureModeIds.size(), 2u);
    EXPECT_EQ(info.failureModeIds[0], "FM001");
    EXPECT_EQ(info.failureModeIds[1], "FM002");
}
