/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of the Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 * PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

#ifndef DIAGNOSIS_TOOL_MODULE_H
#define DIAGNOSIS_TOOL_MODULE_H

#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "rack_error.h"
#include "rack_module.h"
#include "diagnosis_engine.h"

namespace diag {

class DiagnosisToolModule final : public rack::module::RackModule {
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
    RackResult BuildLogTypeToPathMap();
    RackResult StoreFailureTraces() const;
    RackResult GenerateFailureModeView() const;

    std::string dsLogPath_;
    std::string dsClientAccessLogFile_;
    std::string dsClientInfoLogFile_;
    std::string dsWorkerAccessLogFile_;
    std::string dsWorkerInfoLogFile_;
    std::string resourceLogFile_;
    std::string startTimeStr_;
    std::string endTimeStr_;
    std::string randomStr_;
    std::string wittyDir_;
    std::string mergedLogDir_;

    std::unordered_map<std::string, std::vector<std::string>> logTypeToPath_;
    std::unique_ptr<DiagnosisEngine> engine_;
};

} // namespace diag

#endif // DIAGNOSIS_TOOL_MODULE_H
