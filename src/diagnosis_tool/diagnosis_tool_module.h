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

#include <cstddef>
#include <iosfwd>
#include <memory>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "rack_error.h"
#include "rack_module.h"
#include "diagnosis_engine.h"

namespace diag {

class MappedReadFile final {
public:
    explicit MappedReadFile(const std::string &path);
    ~MappedReadFile();
    MappedReadFile(const MappedReadFile &) = delete;
    MappedReadFile &operator=(const MappedReadFile &) = delete;

    bool IsOpen() const;
    std::string_view Content() const;

private:
    void Close();

    int descriptor_ = -1;
    void *data_ = nullptr;
    std::size_t size_ = 0;
};

class DiagnosisToolModule final : public rack::module::RackModule {
public:
    DiagnosisToolModule();
    ~DiagnosisToolModule() override = default;

    RackResult Initialize() override;
    void UnInitialize() override;
    RackResult Start() override;
    void Stop() override;

private:
    enum class LogKind {
        NONE,
        ACCESS,
        RUNTIME,
    };

    struct LineProcessContext {
        const std::string &startTime;
        const std::string &endTime;
        bool &inRange;
        std::ostream &output;
        LogKind kind;
        bool useMappedInput;
        std::vector<std::string_view> &runtimeLines;
    };

    RackResult ParseDiagArgs();
    RackResult ConfigureMergedPath();
    RackResult ExtractLogsByTimeWindow();
    void CollectLogSources(std::unordered_map<std::string, std::vector<std::string>> &outputToSources);
    void ClassifyLogOutputs(const std::unordered_map<std::string, std::vector<std::string>> &outputToSources,
                            std::vector<std::string> &accessOutputs, std::vector<std::string> &runtimeOutputs,
                            std::vector<std::string> &otherOutputs);
    RackResult ProcessClassifiedOutputs(
        const std::unordered_map<std::string, std::vector<std::string>> &outputToSources,
        const std::vector<std::string> &accessOutputs, const std::vector<std::string> &runtimeOutputs,
        const std::vector<std::string> &otherOutputs);
    std::vector<std::string> FindMatchingFiles(const std::string &dir, const std::string &pattern);
    bool ExtractLogLinesByTimeWindow(const std::string &inputPath, const std::string &outputPath, bool append,
                                     LogKind kind);
    void WriteExtractedLine(std::ostream &output, std::string_view line, LogKind kind, bool useMappedInput,
                            std::vector<std::string_view> &runtimeLines) const;
    bool ProcessExtractedLine(std::string_view line, LineProcessContext &ctx) const;
    bool FeedExtractedLog(const std::string &path, LogKind kind);
    RackResult BuildLogTypeToPathMap();
    RackResult StoreFailureTraces() const;

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
