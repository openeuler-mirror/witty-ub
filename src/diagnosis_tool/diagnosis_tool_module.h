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

#include <cstdint>
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
    RackResult ParseDiagArgs();                     // 解析命令行参数并校验
    RackResult ExtractLogsByTimeWindow();           // 根据时间窗提取日志
    void ExtractLogLinesCount(const std::string &filePath, int64_t startTs, int64_t endTs,
                              std::ofstream &outFile, int &count);
    bool ExtractLogLines(const std::string &filePath, const std::string &outputPath,
                         int64_t startTs, int64_t endTs);
    std::vector<std::string> FindMatchingFiles(const std::string &dir,
                                               const std::string &pattern); // 递归搜索匹配的文件

    bool Visit(FailureModeController controller);   // 构建tree静态图和traces命中表
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

    // 命令行参数
    std::string dsLogPath;               // --ds-log-path
    std::string dsClientAccessLogFile;   // --ds-client-access-log-file
    std::string dsClientInfoLogFile;     // --ds-client-info-log-file
    std::string dsWorkerInfoLogFile;     // --ds-worker-info-log-file
    std::string resourceLogFile;         // --resource-log-file
    std::string startTimeStr;
    std::string endTimeStr;
    int64_t startTimestamp = 0;
    int64_t endTimestamp = 0;
    std::string extractedLogDir;
};

} // namespace diag
