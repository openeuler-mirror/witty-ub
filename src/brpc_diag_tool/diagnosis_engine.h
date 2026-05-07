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

#ifndef DIAGNOSIS_ENGINE_H
#define DIAGNOSIS_ENGINE_H
#pragma once

#include <vector>
#include <string>
#include "diagnosis_result.h"
#include "log_def.h"

namespace brpc {

struct DiagnosisRule {
    string faultMode;
    vector<string> keywords;
    bool checkSystemLog;
    bool checkBrpcLog;
    string problemCause;
    string solution;
};

class DiagnosisEngine {
public:
    DiagnosisEngine();
    DiagnosisResult Diagnosis(vector<SystemLog> systemLogs, vector<BrpcLog> brpcLogs);
private:
    vector<DiagnosisRule> rules;
    void InitRules();
    string ToLower(const string& str);
    bool MatchRule(const DiagnosisRule& rule, const vector<SystemLog>& systemLogs,
                   const vector<BrpcLog>& brpcLogs, vector<string>& matchedLogs);
};
}
// 规范：在本文件中定义诊断主函数Diagnosis，如有必要，可以使用诊断代码生成skill添加更多变量和函数定义
#endif