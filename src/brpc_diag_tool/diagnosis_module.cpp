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

#define MODULE_NAME "DIAGNOSIS"

#include "diagnosis_module.h"
#include "logger.h"
#include "ubse_context.h"

namespace brpc {
using namespace ubse::context;

DiagnosisModule::DiagnosisModule() : timestamp_(0) {}

// 初始化模块：从UbseContext中获取命令行参数，设置日志路径和时间戳，创建日志收集器和诊断引擎
RackResult DiagnosisModule::Initialize()
{
    auto &argMap = UbseContext::GetInstance().GetArgMap();

    // 解析必选参数：brpc-log（BRPC日志文件路径）
    auto brpcIt = argMap.find("brpc-log");
    if (brpcIt == argMap.end()) {
        LOG_ERROR << "missing argument brpc-log";
        return RACK_FAIL;
    }
    BrpcLog::logPath = brpcIt->second;

    // 解析必选参数：timestamp（时间戳，用于日志筛选）
    auto tsIt = argMap.find("timestamp");
    if (tsIt == argMap.end()) {
        LOG_ERROR << "missing argument timestamp";
        return RACK_FAIL;
    }
    try {
        timestamp_ = std::stoll(tsIt->second);
    } catch (...) {
        LOG_ERROR << "invalid timestamp value: " << tsIt->second;
        return RACK_FAIL;
    }

    // 解析可选参数：system-log（系统日志文件路径），未指定时默认使用brpc-log同目录下的system.log
    auto sysIt = argMap.find("system-log");
    if (sysIt != argMap.end()) {
        SystemLog::logPath = sysIt->second;
    } else {
        SystemLog::logPath = BrpcLog::logPath.substr(0, BrpcLog::logPath.rfind('/')) + "/system.log";
        LOG_INFO << "system-log not specified, using: " << SystemLog::logPath;
    }

    // 创建日志收集器和诊断引擎实例
    collector_ = std::make_shared<LogCollector>();
    engine_ = std::make_shared<DiagnosisEngine>();

    LOG_INFO << "DiagnosisModule initialized, brpc-log: " << BrpcLog::logPath
             << ", system-log: " << SystemLog::logPath
             << ", timestamp: " << timestamp_;
    return RACK_OK;
}

void DiagnosisModule::UnInitialize()
{
    LOG_INFO << "DiagnosisModule uninitialized";
}

// 启动模块：执行完整的诊断流程（日志收集→诊断分析→结果输出）
RackResult DiagnosisModule::Start()
{
    LOG_INFO << "DiagnosisModule starting log collection";

    // 步骤1：收集系统日志和BRPC日志
    vector<SystemLog> systemLogs = collector_->CollectSystemLog(timestamp_);
    vector<BrpcLog> brpcLogs = collector_->CollectBrpcLog(timestamp_);

    LOG_INFO << "Collected " << systemLogs.size() << " system log entries, "
             << brpcLogs.size() << " brpc log entries";

    // 步骤2：调用诊断引擎进行分析
    DiagnosisResult result = engine_->Diagnosis(systemLogs, brpcLogs);

    // 步骤3：输出诊断结果
    result.OutputResult();

    LOG_INFO << "DiagnosisModule completed";
    return RACK_OK;
}

void DiagnosisModule::Stop()
{
    LOG_INFO << "DiagnosisModule stopped";
}

}
