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

#include "rack_error.h"
#include "rack_module.h"
#include "diagnosis_engine.h"
#include "diagnosis_result.h"
#include "log_collector.h"

namespace brpc {
using namespace rack::module;

// 诊断模块，继承RackModule，集成日志收集、诊断分析和结果输出的完整诊断流程
class DiagnosisModule final : public RackModule {
public:
    DiagnosisModule();
    ~DiagnosisModule() override = default;

    // 初始化模块：解析命令行参数（brpc-log、timestamp、system-log），创建日志收集器和诊断引擎
    RackResult Initialize() override;
    // 反初始化模块
    void UnInitialize() override;
    // 启动模块：执行日志收集→诊断分析→结果输出的完整流程
    RackResult Start() override;
    // 停止模块
    void Stop() override;

private:
    std::shared_ptr<LogCollector> collector_; // 日志收集器
    std::shared_ptr<DiagnosisEngine> engine_; // 诊断引擎
    int64_t timestamp_;                       // 时间戳参数，用于日志筛选
};

} // namespace brpc
