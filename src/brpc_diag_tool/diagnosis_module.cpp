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

#define MODULE_NAME "BRPC_DIAG"

#include "diagnosis_module.h"
#include <cstdlib>
#include <filesystem>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include "logger.h"
#include "ubse_context.h"

namespace brpc {
using namespace ubse::context;

namespace {
constexpr const char *DEFAULT_WITTY_DIR = "/var/witty-ub";
constexpr const char *RESULT_DIRECTORY_NAME = "brpc-diag";
constexpr std::size_t MAX_TASK_ID_LENGTH = 128;
using ArgumentMap = std::unordered_map<std::string, std::string>;

// taskId 会进入 batch 文件名，仅允许安全的 ASCII 字符。
bool IsValidDiagnosisTaskId(std::string_view taskId)
{
    if (taskId.empty() || taskId.size() > MAX_TASK_ID_LENGTH) {
        return false;
    }
    return std::all_of(taskId.begin(), taskId.end(), [](unsigned char character) {
        return (character >= 'a' && character <= 'z') || (character >= 'A' && character <= 'Z') ||
               (character >= '0' && character <= '9') || character == '-' || character == '_';
    });
}

bool ParseBrpcLogArgument(const ArgumentMap &arguments, std::filesystem::path &brpcLogPath)
{
    auto iterator = arguments.find("brpc-log");
    if (iterator == arguments.end()) {
        LOG_ERROR << "missing argument brpc-log";
        return false;
    }
    brpcLogPath = iterator->second;
    return true;
}

bool ParseTaskIdArgument(const ArgumentMap &arguments, std::string &taskId)
{
    auto iterator = arguments.find("task-id");
    if (iterator == arguments.end()) {
        LOG_ERROR << "missing argument task-id";
        return false;
    }
    taskId = iterator->second;
    if (!IsValidDiagnosisTaskId(taskId)) {
        LOG_ERROR << "invalid task-id; expected 1-128 letters, digits, '-' or '_'";
        return false;
    }
    return true;
}

bool ParseTimestampArgument(const ArgumentMap &arguments, std::int64_t &timestamp)
{
    auto iterator = arguments.find("timestamp");
    if (iterator == arguments.end()) {
        // An omitted lower bound means scan the complete log, matching the
        // ParseConfig semantics used by the KVCache parser.
        timestamp = 0;
        return true;
    }
    try {
        std::size_t parsedLength = 0;
        timestamp = std::stoll(iterator->second, &parsedLength);
        if (parsedLength != iterator->second.size() || timestamp < 0) {
            throw std::invalid_argument("timestamp must be a nonnegative integer");
        }
    } catch (...) {
        LOG_ERROR << "invalid timestamp value: " << iterator->second;
        return false;
    }
    return true;
}
} // namespace

DiagnosisModule::DiagnosisModule() = default;

// 初始化模块：从UbseContext中获取命令行参数，设置日志路径和时间戳，创建日志收集器和诊断引擎
RackResult DiagnosisModule::Initialize()
{
    engine_.reset();
    collector_.reset();
    outputPath_.clear();
    taskId_.clear();
    timestamp_ = 0;

    const auto &arguments = UbseContext::GetInstance().GetArgMap();
    std::filesystem::path brpcLogPath;
    if (!ParseBrpcLogArgument(arguments, brpcLogPath)) {
        return RACK_FAIL;
    }
    if (!ParseTaskIdArgument(arguments, taskId_)) {
        return RACK_FAIL;
    }
    if (!ParseTimestampArgument(arguments, timestamp_)) {
        return RACK_FAIL;
    }

    const char *wittyDirEnv = std::getenv("WITTY_DIR");
    const std::filesystem::path wittyDir = wittyDirEnv ? wittyDirEnv : DEFAULT_WITTY_DIR;
    outputPath_ = wittyDir / RESULT_DIRECTORY_NAME;

    collector_ = std::make_unique<LogCollector>(brpcLogPath);
    engine_ = DiagnosisEngine::Create(wittyDir);
    if (!engine_) {
        LOG_ERROR << "failed to initialize diagnosis engine from: " << wittyDir.string();
        collector_.reset();
        return RACK_FAIL;
    }

    LOG_INFO << "DiagnosisModule initialized, brpc-log: " << brpcLogPath.string() << ", task-id: " << taskId_
             << ", output: " << outputPath_.string() << ", timestamp: " << timestamp_;
    return RACK_OK;
}

void DiagnosisModule::UnInitialize()
{
    engine_.reset();
    collector_.reset();
    taskId_.clear();
    LOG_INFO << "DiagnosisModule uninitialized";
}

// 启动模块：执行完整的诊断流程（日志收集→诊断分析→结果输出）
RackResult DiagnosisModule::Start()
{
    LOG_INFO << "DiagnosisModule starting log collection";

    if (!collector_ || !engine_) {
        LOG_ERROR << "DiagnosisModule is not initialized";
        return RACK_FAIL;
    }

    const std::int64_t endTimestamp = LogCollector::CurrentTimestamp();
    std::optional<DiagnosisResult> result = engine_->RunDiagnosis(*collector_, timestamp_, endTimestamp);
    if (!result.has_value()) {
        LOG_ERROR << "failed to read required BRPC log";
        return RACK_FAIL;
    }

    // 步骤3：输出规则快照和本次诊断批次
    if (!result->Dump(outputPath_, taskId_)) {
        return RACK_FAIL;
    }

    LOG_INFO << "DiagnosisModule completed";
    return RACK_OK;
}

void DiagnosisModule::Stop()
{
    LOG_INFO << "DiagnosisModule stopped";
}

} // namespace brpc
