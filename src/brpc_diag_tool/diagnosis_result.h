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

#ifndef DIAGNOSIS_RESULT_H
#define DIAGNOSIS_RESULT_H

#include <json/json.h>

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>
#include "diagnosis_model.h"

namespace brpc {
// 一次诊断的待发布结果。静态规则会输出为 schema 快照，直接命中的日志会输出为 batch JSONL。
class DiagnosisResult {
public:
    // 基于完整规则 DAG 生成稳定 schema，并保存本批次的直接命中事实。
    // 每个可命中的故障模式都必须能经同组件 intra_component 路径映射到至少一个接口。
    bool Build(const std::vector<DiagnosisRule> &rules,
               std::unordered_map<std::size_t, std::vector<DiagnosisLog>> directlyHitLogs, std::int64_t startTimestamp,
               std::int64_t endTimestamp);

    // 按 V2.1 格式将 schema（若尚不存在）和任务的最终 batch 原子发布到 outputDirectory。
    // 同一 taskId 重试时会原子覆盖原有 batch 文件。
    bool Dump(const std::filesystem::path &outputDirectory, const std::string &taskId) const;

private:
    using SchemaNode = FailureModeInfo;
    using FailureToInterfaces = std::vector<std::vector<std::size_t>>;

    struct SchemaEdge {
        std::size_t sourceIndex = 0;
        std::size_t targetIndex = 0;
        DiagnosisEdgeType type = DiagnosisEdgeType::INTRA_COMPONENT;
    };

    struct FailureInterfaceMapping {
        std::size_t failureModeIndex = 0;
        std::vector<std::size_t> interfaceIndices;
        // edges_ 中位于任一同组件接口到该故障模式路径上的边。
        // 输出时会转换成 schema 全局 edges 数组的稳定下标。
        std::vector<std::size_t> subgraphEdgeIndices;
    };

    struct Hit {
        std::size_t failureModeIndex = 0;
        DiagnosisLog log;
        std::optional<std::size_t> interfaceIndex;
        std::string interfaceResolution = "unresolved";
    };

    void Reset(std::int64_t startTimestamp, std::int64_t endTimestamp);
    bool BuildNodes(const std::vector<DiagnosisRule> &rules);
    bool BuildEdges(const std::vector<DiagnosisRule> &rules);
    bool BuildMappings(const std::vector<DiagnosisRule> &rules);
    bool BuildMappingSubgraphs(const std::vector<DiagnosisRule> &rules);
    bool CollectReachableInterfaces(const std::vector<DiagnosisRule> &rules, std::size_t interfaceIndex,
                                    FailureToInterfaces &failureToInterfaces) const;
    bool FinalizeMappings(const std::vector<DiagnosisRule> &rules, FailureToInterfaces &failureToInterfaces);
    bool BuildHits(const std::vector<DiagnosisRule> &rules,
                   std::unordered_map<std::size_t, std::vector<DiagnosisLog>> directlyHitLogs);
    void ResolveHitInterfaces(const std::vector<DiagnosisRule> &rules);
    std::vector<std::size_t> FindCommonInterfaceCandidates(const std::vector<DiagnosisRule> &rules,
                                                           const FailureToInterfaces &candidatesByFailure,
                                                           DiagnosisComponent component,
                                                           const std::vector<std::size_t> &hitIndices,
                                                           std::vector<std::size_t> &componentHitIndices) const;
    std::vector<std::size_t> FindCrossComponentAnchors(const std::vector<DiagnosisRule> &rules,
                                                       DiagnosisComponent component,
                                                       const std::vector<std::size_t> &hitIndices) const;
    void ResolveRequestComponentInterfaces(const std::vector<DiagnosisRule> &rules,
                                           const FailureToInterfaces &candidatesByFailure, DiagnosisComponent component,
                                           const std::vector<std::size_t> &hitIndices);

    Json::Value BuildSchemaPayload() const;
    Json::Value BuildSchemaNodes() const;
    Json::Value BuildSchemaNode(const SchemaNode &failureMode) const;
    Json::Value BuildSchemaEdges(const std::vector<std::size_t> &edgeOrder) const;
    Json::Value BuildSchemaMappings(const std::vector<std::size_t> &edgeOrder) const;
    std::vector<std::size_t> BuildSchemaEdgeOrder() const;
    Json::Value BuildHit(const Hit &storedHit, std::size_t hitIndex, const std::string &batchId) const;
    std::string BuildBatchContent(const std::string &taskId, const std::string &batchId, const std::string &schemaId,
                                  std::int64_t createdAtTimestamp) const;
    bool PublishSchema(const std::filesystem::path &outputDirectory, const Json::Value &schemaPayload,
                       std::string &schemaId) const;

    std::vector<SchemaNode> nodes_;
    std::vector<SchemaEdge> edges_;
    std::vector<FailureInterfaceMapping> mappings_;
    std::vector<Hit> hits_;
    std::int64_t startTimestamp_ = 0;
    std::int64_t endTimestamp_ = 0;
};

} // namespace brpc

#endif // DIAGNOSIS_RESULT_H
