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

#include <vector>
#include "diagnosis_result.h"
#include "log_def.h"

namespace brpc {
class DiagnosisEngine {
public:
    DiagnosisResult Diagnosis(vector<SystemLog> systemLogs, vector<BrpcLog> brpcLogs);    
};
}

//规范：在本文件中定义诊断主函数Diagnosis，如有必要，可以使用诊断代码生成skill添加更多变量和函数定义