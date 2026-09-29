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
#include "failure_mode_controller.h"

TEST(FailureModeController, InitialState) {
    diag::FailureModeDescriptor desc;
    desc.id = "FM001";
    diag::FailureMode fm(std::move(desc));
    auto fmc = std::make_shared<diag::FailureModeController>(std::make_shared<diag::FailureMode>(std::move(fm)));
    EXPECT_EQ(fmc->GetHitCount(), 0);
    EXPECT_TRUE(fmc->GetTraceIdToFailureLogInfo().empty());
    EXPECT_TRUE(fmc->GetSubValidFailureModeIds().empty());
}

TEST(FailureModeController, HitIncrementsCount) {
    diag::FailureModeDescriptor desc;
    desc.id = "FM001";
    diag::FailureMode fm(std::move(desc));
    auto fmc = std::make_shared<diag::FailureModeController>(std::make_shared<diag::FailureMode>(std::move(fm)));

    // Create a minimal FailureLogInfo
    std::vector<std::string> fields(8, "");
    fields[0] = "2024-01-15 10:30:00";
    fields[1] = "I";
    fields[2] = "file.cpp:42";
    fields[3] = "pod1";
    fields[4] = "123:456";
    fields[5] = "trace1";
    fields[6] = "cluster1";
    fields[7] = "message";
    auto logInfo = std::make_shared<diag::FailureLogInfo>(fields, "raw log");

    fmc->Hit("trace1", logInfo);
    EXPECT_EQ(fmc->GetHitCount(), 1);
    EXPECT_EQ(fmc->GetTraceIdToFailureLogInfo().size(), 1u);
}

TEST(FailureModeController, InsertSubValidId) {
    diag::FailureModeDescriptor desc;
    desc.id = "FM001";
    diag::FailureMode fm(std::move(desc));
    auto fmc = std::make_shared<diag::FailureModeController>(std::make_shared<diag::FailureMode>(std::move(fm)));
    fmc->InsertSubValidFailureModeId("FM002");
    EXPECT_EQ(fmc->GetSubValidFailureModeIds().size(), 1u);
    EXPECT_EQ(*fmc->GetSubValidFailureModeIds().begin(), "FM002");
}

TEST(FailureModeController, GetFailureMode) {
    diag::FailureModeDescriptor desc;
    desc.id = "FM001";
    desc.name = "TestFailure";
    auto fm = std::make_shared<diag::FailureMode>(std::move(desc));
    auto fmc = std::make_shared<diag::FailureModeController>(fm);
    EXPECT_EQ(fmc->GetFailureMode()->GetId(), "FM001");
    EXPECT_EQ(fmc->GetFailureMode()->GetName(), "TestFailure");
}
