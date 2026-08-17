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

#include <cstddef>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>
#include "diagnosis_result.h"
#include "log_collector.h"

namespace brpc {
class DiagnosisEngine {
public:
    DiagnosisEngine() = default;

    static std::unique_ptr<DiagnosisEngine> Create(const std::filesystem::path &wittyDir);

    std::optional<DiagnosisResult> RunDiagnosis(const LogCollector &collector, std::int64_t startTimestamp,
                                                std::int64_t endTimestamp) const;

private:
    using FunctionNameToRuleIndices = std::unordered_map<std::string, std::vector<std::size_t>>;
    using FilenameToFunctionNameToRuleIndices = std::unordered_map<std::string, FunctionNameToRuleIndices>;

    struct MatchState {
        std::unordered_map<std::size_t, std::vector<DiagnosisLog>> ruleIndexToLogs;
    };

    std::vector<DiagnosisRule> rules_; // 唯一数据存储：规则数组（含父子下标），无冗余索引
    // BRPC 日志按文件名、函数名两级索引 ubsocket/umq 具体故障节点；公共 API 根节点不进入索引。
    FilenameToFunctionNameToRuleIndices brpcfilenameToFunctionNameToRuleIndices_;
    // URMA 规则也按内层 urma 日志解析出的文件名、函数名建立两级索引。
    FilenameToFunctionNameToRuleIndices urmaFilenameToFunctionNameToRuleIndices_;

    // 规则加载与索引构建
    // 从 data/{ubsocket,umq,urma}/ 三个故障模式 JSON 与 failure_mode_tree.json 装载规则
    // idToIndex 仅在装载期间使用，调用方作为局部变量传入
    bool LoadRulesFromJson(const std::filesystem::path &wittyDir);
    bool LoadComponentFailureModes(const std::string &path, std::unordered_map<std::string, std::size_t> &idToIndex);
    bool LoadFailureModeTree(const std::string &path, const std::unordered_map<std::string, std::size_t> &idToIndex);
    // 装载完成后构建日志匹配索引。
    void BuildRuleIndices();

    // 规则关键字解析与匹配
    // 解析"依次匹配`错误片段1`、`错误片段2`"格式的关键字，所有反引号内容均纳入 keywords；
    // "向下级匹配"返回空 vector
    static std::vector<std::string> ParseKeywords(const std::string &phenomenon);
    // 按顺序匹配所有关键字；成功时返回关键字总长度，失败时返回 nullopt。
    static std::optional<std::size_t> MatchKeywords(const DiagnosisRule &rule, const std::string &text);

    // 单条日志诊断与最优规则选择
    void ProcessLog(BrpcLog &&log, MatchState &state) const;
    // 多条规则同时匹配时，以所有固定关键字的总长度衡量规则的匹配特异性；
    // 长度相同时选择规则文件中顺序靠前的一条，确保每条日志只归属一个故障模式。
    void SelectBestHit(BrpcLog &&log, const std::vector<std::size_t> &candidateIndices, MatchState &state) const;
};
} // namespace brpc
// 规范：在本文件中定义诊断主函数Diagnosis，如有必要，可以使用诊断代码生成skill添加更多变量和函数定义

#endif // DIAGNOSIS_ENGINE_H
