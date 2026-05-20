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

#pragma once

#include <string>
#include <unordered_map>
#include <vector>
#include "rack_error.h"
#include "rack_module.h"
#include "failure_log_info.h"
#include "failure_mode.h"
#include "failure_mode_controller.h"

namespace diag {
using namespace rack::module;

// 诊断模块，继承RackModule，执行故障树判断逻辑
class DiagnosisToolModule final : public RackModule {
public:
    DiagnosisToolModule();
    ~DiagnosisToolModule() override = default;
    // 初始化故障树Json
    void InitializeFailureModeTree();
    // 初始化模块
    RackResult Initialize() override;
    // 反初始化模块
    void UnInitialize() override;
    // 启动模块
    RackResult Start() override;
    // 停止模块
    void Stop() override;

private:
    bool VisitKvCache(FailureModeController controller);
    bool VisitUrma(FailureModeController controller);   // 构建urma tree静态图和traces命中表
    void StartKvcache(const std::vector<std::string> &subRootFailureModes);
    void StartUrma(const std::vector<std::string> &subRootFailureModes);

private:
    std::unordered_map<std::string, std::unordered_map<std::string, std::vector<std::string>>> failureModeJson;
    std::unordered_map<std::string, std::shared_ptr<FailureMode>> failureModeInstanceMap;
    std::unordered_map<std::string, std::vector<std::string>> subRootFailureModesMap;

    std::unordered_map<std::string, FailureModeController>
        failureModeIdToController; // (failureLogInfo ->) failureModeId -> failureModeController (-> failureMode)
    std::unordered_map<std::string, std::vector<FailureLogInfo>> traces; // traceId -> logs
    std::unordered_set<std::string> allFailureModes;                     // failureModeId
    std::unordered_set<std::string> childFailureModes;                   // failureModeId
    std::unordered_set<std::string> rootFailureModes;                    // failureModeId
};

} // namespace diag
