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

#ifndef DIAGNOSIS_TOOL_MODULE_H
#define DIAGNOSIS_TOOL_MODULE_H

#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "rack_error.h"
#include "rack_module.h"
#include "failure_log_info.h"
#include "failure_mode_controller.h"

namespace diag {
using namespace rack::module;

class DiagnosisToolModule final : public RackModule {
public:
    DiagnosisToolModule();
    ~DiagnosisToolModule() override = default;

    RackResult Initialize() override;
    void UnInitialize() override;
    RackResult Start() override;
    void Stop() override;

private:
    RackResult ParseDiagArgs();
    RackResult ConfigureMergedPath();
    RackResult ExtractLogsByTimeWindow();
    std::vector<std::string> FindMatchingFiles(const std::string &dir, const std::string &pattern);
    bool ExtractLogLinesByTimeWindow(const std::string &inputPath, const std::string &outputPath, bool append = false);
    RackResult BuildFailureModeTree();
    RackResult BuildLogTypeToPathMap();
    RackResult AnalyzeAccessLogs();
    RackResult AnalyzeRuntimeLogs();
    RackResult MergeFailureModeByTraceId();
    RackResult StoreFailureTraces();
    RackResult GenerateFailureModeView();

private:
    // 命令行参数
    std::string dsLogPath_;
    std::string dsClientAccessLogFile_;
    std::string dsClientInfoLogFile_;
    std::string dsWorkerAccessLogFile_;
    std::string dsWorkerInfoLogFile_;
    std::string resourceLogFile_;
    std::string startTimeStr_;
    std::string endTimeStr_;
    std::string randomStr_;

    int64_t startTimestamp_;
    int64_t endTimestamp_;

    std::string mergedLogDir_;

    // 映射表
    std::unordered_map<std::string, std::vector<std::string>> logTypeToPath_; // log type (access/runtime) -> path
    std::unordered_map<std::string, FailureModeController>
        failureModeIdToController_; // failure mode id -> failure mode controller (-> failure mode)
    std::unordered_map<std::string, std::vector<std::string>>
        childToParentFailureModeIds_; // child failure mode id -> parent failure mode id[]
    std::unordered_map<std::string, std::vector<std::string>>
        moduleToRootFailureModeIds_; // module name -> root failure mode id[]
    std::unordered_map<std::string, std::unordered_map<std::string, std::vector<std::string>>>
        failureModeJson_; // original json data
    std::unordered_map<int, std::string>
        statusCodeToFailureModeId_;                            // status code -> failure mode id (第一轮筛选的结果)
    std::unordered_map<std::string, int> traceIdToStatusCode_; // trace id -> status code (第一轮筛选的结果)
    std::unordered_map<std::string, std::vector<std::shared_ptr<FailureLogInfo>>>
        traceIdToUrmaFailureLogInfos_; // trace id -> urma failure log info[]（用于临时存放urma故障日志，最终会合并到下一个表）
    std::unordered_map<std::string, std::vector<std::shared_ptr<FailureLogInfo>>>
        traceIdToFailureLogInfos_; // trace id -> failure log info[]（最终结果）
    std::unordered_map<std::string, std::vector<std::string>>
        traceIdToFailureModeIds_;                             // trace id -> failure mode id[]（最终结果）
    std::unordered_set<std::string> rootValidFailureModeIds_; // failureModeId
};
} // namespace diag

#endif
