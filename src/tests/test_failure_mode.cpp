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
#include "failure_mode.h"

TEST(FailureMode, GettersReturnCtorValues) {
    diag::FailureModeDescriptor desc;
    desc.id = "FM001";
    desc.name = "TestFailure";
    desc.phenomenon = "test phenomenon";
    desc.cause = "test cause";
    desc.suggestion = "test suggestion";
    desc.filename = "test.cpp";
    desc.functionName = "testFunc";
    desc.errorCode = "ERR001";
    desc.nodeType = diag::FailureModeNodeType::URMA_INTERFACE;

    diag::FailureMode fm(std::move(desc));
    EXPECT_EQ(fm.GetId(), "FM001");
    EXPECT_EQ(fm.GetName(), "TestFailure");
    EXPECT_EQ(fm.GetPhenomenon(), "test phenomenon");
    EXPECT_EQ(fm.GetRootCauseDesc(), "test cause");
    EXPECT_EQ(fm.GetFixSuggDesc(), "test suggestion");
    EXPECT_EQ(fm.GetValidationMethodDesc(), "test phenomenon");
    EXPECT_EQ(fm.GetFilename(), "test.cpp");
    EXPECT_EQ(fm.GetFunctionName(), "testFunc");
    ASSERT_TRUE(fm.GetErrorCode().has_value());
    EXPECT_EQ(*fm.GetErrorCode(), "ERR001");
    EXPECT_EQ(fm.GetNodeType(), diag::FailureModeNodeType::URMA_INTERFACE);
}

TEST(FailureMode, IsPublicInterface) {
    diag::FailureModeDescriptor desc;
    desc.nodeType = diag::FailureModeNodeType::URMA_INTERFACE;
    diag::FailureMode fm(std::move(desc));
    EXPECT_TRUE(fm.IsPublicInterface());
    EXPECT_FALSE(fm.IsAccessEntry());
}

TEST(FailureMode, IsAccessEntry) {
    diag::FailureModeDescriptor desc;
    desc.nodeType = diag::FailureModeNodeType::ACCESS_LOG_ENTRY;
    diag::FailureMode fm(std::move(desc));
    EXPECT_FALSE(fm.IsPublicInterface());
    EXPECT_TRUE(fm.IsAccessEntry());
}

TEST(FailureMode, NoErrorCode) {
    diag::FailureModeDescriptor desc;
    desc.nodeType = diag::FailureModeNodeType::RUNTIME_LOG;
    diag::FailureMode fm(std::move(desc));
    EXPECT_FALSE(fm.GetErrorCode().has_value());
}
