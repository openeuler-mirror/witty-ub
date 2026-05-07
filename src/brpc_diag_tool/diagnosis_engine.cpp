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

#include "diagnosis_engine.h"
#include <algorithm>
#include <cctype>
#include <sstream>
#include "logger.h"

namespace brpc {

DiagnosisEngine::DiagnosisEngine()
{
    InitRules();
}

void DiagnosisEngine::InitRules()
{
    rules = {{"建链超时/RPC定界超时",
              {"reached timeout"},
              true,
              false,
              "brpc设置的通信或者建链时间太小",
              "根据实际场景设置brpc通信或者建链的时长"},
             {"建链超时/RPC定界超时",
              {"timeout"},
              false,
              true,
              "brpc设置的通信或者建链时间太小",
              "根据实际场景设置brpc通信或者建链的时长"},
             {"初始化内存失败",
              {"buf alloc failed"},
              true,
              false,
              "初始化设置的内存小于block size，或者小于实际需要发送的数据大小",
              "根据配置block size（RPC_ADPT_BLOCK_TYPE）和发送数据大小，合理分配内存（RPC_ADPT_POOL_INITIAL_SIZE）"}};
}

string DiagnosisEngine::ToLower(const string &str)
{
    string result = str;
    transform(result.begin(), result.end(), result.begin(), [](unsigned char c) { return tolower(c); });
    return result;
}

bool DiagnosisEngine::MatchRule(const DiagnosisRule &rule, const vector<SystemLog> &systemLogs,
                                const vector<BrpcLog> &brpcLogs, vector<string> &matchedLogs)
{
    if (rule.checkSystemLog) {
        for (const auto &log : systemLogs) {
            string lowerText = ToLower(log.text);
            bool allMatched = true;
            for (const auto &keyword : rule.keywords) {
                if (lowerText.find(ToLower(keyword)) == string::npos) {
                    allMatched = false;
                    break;
                }
            }
            if (allMatched) {
                matchedLogs.push_back(log.text);
            }
        }
        if (!matchedLogs.empty()) {
            return true;
        }
    }

    if (rule.checkBrpcLog) {
        for (const auto &log : brpcLogs) {
            string lowerText = ToLower(log.text);
            bool allMatched = true;
            for (const auto &keyword : rule.keywords) {
                if (lowerText.find(ToLower(keyword)) == string::npos) {
                    allMatched = false;
                    break;
                }
            }
            if (allMatched) {
                matchedLogs.push_back(log.text);
            }
        }
        if (!matchedLogs.empty()) {
            return true;
        }
    }

    return false;
}

DiagnosisResult DiagnosisEngine::Diagnosis(vector<SystemLog> systemLogs, vector<BrpcLog> brpcLogs)
{
    DiagnosisResult result;

    for (const auto &rule : rules) {
        vector<string> matchedLogs;
        if (MatchRule(rule, systemLogs, brpcLogs, matchedLogs)) {
            ostringstream oss;
            oss << "故障模式: " << rule.faultMode << "; ";
            oss << "故障日志: ";
            for (size_t i = 0; i < matchedLogs.size(); ++i) {
                if (i > 0) {
                    oss << ",";
                }
                oss << matchedLogs[i];
            }
            oss << "; 问题原因: " << rule.problemCause;
            oss << "; 解决方法: " << rule.solution;

            result.result = oss.str();
            return result;
        }
    }

    result.result =
        "故障模式: 未知故障; 故障日志: ; 问题原因: 未匹配到已知故障模式; 解决方法: 请检查日志并联系技术支持";
    return result;
}

} // namespace brpc
