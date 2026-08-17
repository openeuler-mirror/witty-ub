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

#include "diagnosis_result.h"
#include <fcntl.h>
#include <json/json.h>
#include <openssl/rand.h>
#include <openssl/sha.h>
#include <sys/stat.h>
#include <unistd.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <chrono>
#include <cstring>
#include <iomanip>
#include <map>
#include <numeric>
#include <sstream>
#include <string_view>
#include <tuple>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>
#include "diagnosis_engine.h"
#include "logger.h"

namespace brpc {

namespace {
constexpr int SCHEMA_FORMAT_VERSION = 1;
constexpr int BATCH_FORMAT_VERSION = 2;
constexpr std::int64_t MICROSECONDS_PER_SECOND = 1000000;
constexpr int NUM_2 = 2;
constexpr int NUM_4 = 4;
constexpr int NUM_6 = 6;
constexpr int NUM_8 = 8;
constexpr int NUM_10 = 10;
constexpr size_t BYTES_SIZE = 16;
constexpr size_t INDEX_6 = 6;
constexpr size_t INDEX_8 = 8;

std::vector<std::size_t> SortedIntersection(const std::vector<std::size_t> &left, const std::vector<std::size_t> &right)
{
    std::vector<std::size_t> intersection;
    std::set_intersection(left.begin(), left.end(), right.begin(), right.end(), std::back_inserter(intersection));
    return intersection;
}

bool WriteAll(int fd, std::string_view content)
{
    while (!content.empty()) {
        const ssize_t written = ::write(fd, content.data(), content.size());
        if (written < 0) {
            if (errno == EINTR) {
                continue;
            }
            return false;
        }
        if (written == 0) {
            errno = EIO;
            return false;
        }
        content.remove_prefix(static_cast<std::size_t>(written));
    }
    return true;
}

bool SyncDirectory(const std::filesystem::path &directory)
{
    const int fd = ::open(directory.c_str(), O_RDONLY | O_DIRECTORY);
    if (fd < 0) {
        return false;
    }
    const bool success = ::fsync(fd) == 0;
    const int savedError = success ? 0 : errno;
    ::close(fd);
    if (!success) {
        errno = savedError;
    }
    return success;
}

bool WriteAtomically(const std::filesystem::path &outputPath, std::string_view content)
{
    const std::filesystem::path directory = outputPath.parent_path();
    const std::string tempPattern = (directory / ("." + outputPath.filename().string() + ".tmp.XXXXXX")).string();
    std::vector<char> tempName(tempPattern.begin(), tempPattern.end());
    tempName.push_back('\0');
    const int fd = ::mkstemp(tempName.data());
    if (fd < 0) {
        LOG_ERROR << "failed to create temporary diagnosis output: " << std::strerror(errno);
        return false;
    }

    int savedError = 0;
    bool success = ::fchmod(fd, S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH) == 0 && WriteAll(fd, content);
    if (!success) {
        savedError = errno;
    }
    if (success && ::fsync(fd) != 0) {
        success = false;
        savedError = errno;
    }
    if (::close(fd) != 0 && success) {
        success = false;
        savedError = errno;
    }

    const std::filesystem::path tempPath(tempName.data());
    if (!success) {
        LOG_ERROR << "failed to write diagnosis output: " << std::strerror(savedError);
        std::error_code removeError;
        std::filesystem::remove(tempPath, removeError);
        return false;
    }

    std::error_code renameError;
    std::filesystem::rename(tempPath, outputPath, renameError);
    if (renameError) {
        LOG_ERROR << "failed to publish diagnosis output " << outputPath.string() << ": " << renameError.message();
        std::error_code removeError;
        std::filesystem::remove(tempPath, removeError);
        return false;
    }
    if (!SyncDirectory(directory)) {
        LOG_ERROR << "failed to sync diagnosis output directory: " << std::strerror(errno);
        return false;
    }
    return true;
}

std::string JsonString(const Json::Value &value, const std::string &indentation)
{
    Json::StreamWriterBuilder writer;
    writer["indentation"] = indentation;
    return Json::writeString(writer, value);
}

std::string Sha256Hex(std::string_view content)
{
    std::array<unsigned char, SHA256_DIGEST_LENGTH> digest{};
    SHA256(reinterpret_cast<const unsigned char *>(content.data()), content.size(), digest.data());
    std::ostringstream result;
    result << std::hex << std::setfill('0');
    for (unsigned char byte : digest) {
        result << std::setw(NUM_2) << static_cast<unsigned int>(byte);
    }
    return result.str();
}

std::optional<std::string> GenerateUuidV7(std::int64_t createdAtTimestamp)
{
    std::array<unsigned char, BYTES_SIZE> bytes{};
    if (RAND_bytes(bytes.data(), static_cast<int>(bytes.size())) != 1) {
        LOG_ERROR << "failed to generate cryptographically secure randomness for UUID";
        return std::nullopt;
    }

    const std::uint64_t unixMilliseconds = static_cast<std::uint64_t>(createdAtTimestamp / 1000);
    for (std::size_t i = 0; i < INDEX_6; ++i) {
        bytes[i] = static_cast<unsigned char>((unixMilliseconds >> ((5U - i) * 8U)) & 0xffU);
    }
    bytes[INDEX_6] = static_cast<unsigned char>((bytes[INDEX_6] & 0x0fU) | 0x70U);
    bytes[INDEX_8] = static_cast<unsigned char>((bytes[INDEX_8] & 0x3fU) | 0x80U);

    std::ostringstream result;
    result << std::hex << std::setfill('0');
    for (std::size_t i = 0; i < bytes.size(); ++i) {
        if (i == NUM_4 || i == NUM_6 || i == NUM_8 || i == NUM_10) {
            result << '-';
        }
        result << std::setw(NUM_2) << static_cast<unsigned int>(bytes[i]);
    }
    return result.str();
}

void SetNullableString(Json::Value &object, const char *field, const std::string &value)
{
    if (value.empty() || value == "-") {
        object[field] = Json::nullValue;
    } else {
        object[field] = value;
    }
}

} // namespace

bool DiagnosisResult::Build(const std::vector<DiagnosisRule> &rules,
                            std::unordered_map<std::size_t, std::vector<DiagnosisLog>> directlyHitLogs,
                            std::int64_t startTimestamp, std::int64_t endTimestamp)
{
    Reset(startTimestamp, endTimestamp);
    if (startTimestamp < 0 || endTimestamp < startTimestamp) {
        LOG_ERROR << "invalid diagnosis interval: [" << startTimestamp << ", " << endTimestamp << ")";
        return false;
    }
    if (!BuildNodes(rules) || !BuildEdges(rules) || !BuildMappings(rules) ||
        !BuildHits(rules, std::move(directlyHitLogs))) {
        return false;
    }
    ResolveHitInterfaces(rules);
    return true;
}

void DiagnosisResult::Reset(std::int64_t startTimestamp, std::int64_t endTimestamp)
{
    nodes_.clear();
    edges_.clear();
    mappings_.clear();
    hits_.clear();
    startTimestamp_ = startTimestamp;
    endTimestamp_ = endTimestamp;
}

bool DiagnosisResult::BuildNodes(const std::vector<DiagnosisRule> &rules)
{
    nodes_.reserve(rules.size());
    std::unordered_set<std::string> nodeIds;
    for (const DiagnosisRule &rule : rules) {
        if (!nodeIds.insert(rule.failureMode.id).second) {
            LOG_ERROR << "duplicate schema node id: " << rule.failureMode.id;
            return false;
        }
        nodes_.push_back(rule.failureMode);
    }
    return true;
}

bool DiagnosisResult::BuildEdges(const std::vector<DiagnosisRule> &rules)
{
    for (std::size_t sourceIndex = 0; sourceIndex < rules.size(); ++sourceIndex) {
        for (std::size_t targetIndex : rules[sourceIndex].localChildIndices) {
            if (targetIndex >= rules.size()) {
                LOG_ERROR << "invalid intra-component edge target index";
                return false;
            }
            edges_.push_back({sourceIndex, targetIndex, DiagnosisEdgeType::INTRA_COMPONENT});
        }
        for (std::size_t targetIndex : rules[sourceIndex].crossChildIndices) {
            if (targetIndex >= rules.size()) {
                LOG_ERROR << "invalid cross-component edge target index";
                return false;
            }
            edges_.push_back({sourceIndex, targetIndex, DiagnosisEdgeType::CROSS_COMPONENT});
        }
    }
    std::sort(edges_.begin(), edges_.end(), [](const SchemaEdge &left, const SchemaEdge &right) {
        return std::tie(left.sourceIndex, left.targetIndex, left.type) <
               std::tie(right.sourceIndex, right.targetIndex, right.type);
    });
    const auto isSameEdge = [](const SchemaEdge &left, const SchemaEdge &right) {
        const bool sameSource = left.sourceIndex == right.sourceIndex;
        const bool sameTarget = left.targetIndex == right.targetIndex;
        return sameSource && sameTarget && left.type == right.type;
    };
    edges_.erase(std::unique(edges_.begin(), edges_.end(), isSameEdge), edges_.end());
    return true;
}

bool DiagnosisResult::CollectReachableInterfaces(const std::vector<DiagnosisRule> &rules, std::size_t interfaceIndex,
                                                 FailureToInterfaces &failureToInterfaces) const
{
    std::vector<std::size_t> stack{interfaceIndex};
    std::vector<bool> visited(rules.size(), false);
    while (!stack.empty()) {
        const std::size_t current = stack.back();
        stack.pop_back();
        if (visited[current]) {
            continue;
        }
        visited[current] = true;
        if (!rules[current].failureMode.publicApi) {
            failureToInterfaces[current].push_back(interfaceIndex);
        }
        for (std::size_t child : rules[current].localChildIndices) {
            if (child >= rules.size() ||
                rules[child].failureMode.component != rules[interfaceIndex].failureMode.component) {
                LOG_ERROR << "invalid component in interface mapping path from "
                          << rules[interfaceIndex].failureMode.id;
                return false;
            }
            stack.push_back(child);
        }
    }
    return true;
}

bool DiagnosisResult::FinalizeMappings(const std::vector<DiagnosisRule> &rules,
                                       FailureToInterfaces &failureToInterfaces)
{
    for (std::size_t failureIndex = 0; failureIndex < rules.size(); ++failureIndex) {
        if (rules[failureIndex].failureMode.publicApi) {
            continue;
        }
        auto &interfaceIndices = failureToInterfaces[failureIndex];
        std::sort(interfaceIndices.begin(), interfaceIndices.end(), [&rules](std::size_t left, std::size_t right) {
            return rules[left].failureMode.id < rules[right].failureMode.id;
        });
        interfaceIndices.erase(std::unique(interfaceIndices.begin(), interfaceIndices.end()), interfaceIndices.end());
        if (interfaceIndices.empty()) {
            LOG_ERROR << "failure mode has no reachable public interface: " << rules[failureIndex].failureMode.id;
            return false;
        }
        mappings_.push_back({failureIndex, std::move(interfaceIndices), {}});
    }
    return true;
}

bool DiagnosisResult::BuildMappings(const std::vector<DiagnosisRule> &rules)
{
    FailureToInterfaces failureToInterfaces(rules.size());
    for (std::size_t interfaceIndex = 0; interfaceIndex < rules.size(); ++interfaceIndex) {
        if (rules[interfaceIndex].failureMode.publicApi &&
            !CollectReachableInterfaces(rules, interfaceIndex, failureToInterfaces)) {
            return false;
        }
    }
    return FinalizeMappings(rules, failureToInterfaces) && BuildMappingSubgraphs(rules);
}

bool DiagnosisResult::BuildMappingSubgraphs(const std::vector<DiagnosisRule> &rules)
{
    std::vector<std::vector<std::size_t>> localParents(rules.size());
    for (std::size_t parentIndex = 0; parentIndex < rules.size(); ++parentIndex) {
        for (std::size_t childIndex : rules[parentIndex].localChildIndices) {
            if (childIndex >= rules.size()) {
                LOG_ERROR << "invalid intra-component edge target index";
                return false;
            }
            localParents[childIndex].push_back(parentIndex);
        }
    }

    for (FailureInterfaceMapping &mapping : mappings_) {
        std::vector<bool> reachableFromInterface(rules.size(), false);
        std::vector<std::size_t> pending = mapping.interfaceIndices;
        while (!pending.empty()) {
            const std::size_t current = pending.back();
            pending.pop_back();
            if (reachableFromInterface[current])
                continue;
            reachableFromInterface[current] = true;
            for (std::size_t childIndex : rules[current].localChildIndices) {
                pending.push_back(childIndex);
            }
        }

        std::vector<bool> canReachFailure(rules.size(), false);
        pending = {mapping.failureModeIndex};
        while (!pending.empty()) {
            const std::size_t current = pending.back();
            pending.pop_back();
            if (canReachFailure[current])
                continue;
            canReachFailure[current] = true;
            for (std::size_t parentIndex : localParents[current]) {
                pending.push_back(parentIndex);
            }
        }

        for (std::size_t edgeIndex = 0; edgeIndex < edges_.size(); ++edgeIndex) {
            const SchemaEdge &edge = edges_[edgeIndex];
            if (edge.type == DiagnosisEdgeType::INTRA_COMPONENT && reachableFromInterface[edge.sourceIndex] &&
                canReachFailure[edge.targetIndex]) {
                mapping.subgraphEdgeIndices.push_back(edgeIndex);
            }
        }
        if (mapping.subgraphEdgeIndices.empty()) {
            LOG_ERROR << "failure mode has no interface-to-failure subgraph: "
                      << rules[mapping.failureModeIndex].failureMode.id;
            return false;
        }
    }
    return true;
}

bool DiagnosisResult::BuildHits(const std::vector<DiagnosisRule> &rules,
                                std::unordered_map<std::size_t, std::vector<DiagnosisLog>> directlyHitLogs)
{
    for (auto &entry : directlyHitLogs) {
        if (entry.first >= rules.size() || rules[entry.first].failureMode.publicApi) {
            LOG_ERROR << "invalid directly hit rule index: " << entry.first;
            return false;
        }
        for (DiagnosisLog &log : entry.second) {
            if (log.timestamp < startTimestamp_ || log.timestamp >= endTimestamp_) {
                LOG_ERROR << "hit timestamp is outside diagnosis interval for failure mode "
                          << rules[entry.first].failureMode.id;
                return false;
            }
            hits_.push_back({entry.first, std::move(log)});
        }
    }
    std::sort(hits_.begin(), hits_.end(), [this](const Hit &left, const Hit &right) {
        return std::make_tuple(left.log.timestamp, nodes_[left.failureModeIndex].id, left.log.text) <
               std::make_tuple(right.log.timestamp, nodes_[right.failureModeIndex].id, right.log.text);
    });

    // The scan interval is only an input filter.  Batch metadata describes the
    // data that was actually imported, otherwise an omitted lower bound (Unix
    // epoch) makes every timeline query span decades.  The public API exposes
    // second-resolution timestamps, so make the half-open upper bound the next
    // whole second to ensure the final hit remains queryable after formatting.
    if (!hits_.empty()) {
        startTimestamp_ = hits_.front().log.timestamp;
        endTimestamp_ = (hits_.back().log.timestamp / MICROSECONDS_PER_SECOND + 1) * MICROSECONDS_PER_SECOND;
    }
    return true;
}

void DiagnosisResult::ResolveHitInterfaces(const std::vector<DiagnosisRule> &rules)
{
    FailureToInterfaces candidatesByFailure(rules.size());
    for (const FailureInterfaceMapping &mapping : mappings_) {
        candidatesByFailure[mapping.failureModeIndex] = mapping.interfaceIndices;
    }

    // A singleton static mapping is already an exact runtime attribution.
    for (Hit &hit : hits_) {
        const auto &candidates = candidatesByFailure[hit.failureModeIndex];
        if (candidates.size() == 1) {
            hit.interfaceIndex = candidates.front();
            hit.interfaceResolution = "static_unique";
        }
    }

    // One (pod, Thread) represents one independent request.  Within that
    // request, directly-hit modes from one component belong to the same causal
    // failure chain.  Intersect their candidate public APIs, then use observed
    // cross-component caller edges as an additional hard constraint.
    using RequestKey = std::pair<std::string, int>;
    std::map<RequestKey, std::vector<std::size_t>> requestHits;
    for (std::size_t hitIndex = 0; hitIndex < hits_.size(); ++hitIndex) {
        const Hit &hit = hits_[hitIndex];
        if (hit.log.threadId.has_value() && !hit.log.podIp.empty()) {
            requestHits[{hit.log.podIp, *hit.log.threadId}].push_back(hitIndex);
        }
    }

    const std::vector<DiagnosisComponent> requestComponents = {
        DiagnosisComponent::UBSOCKET,
        DiagnosisComponent::UMQ,
        DiagnosisComponent::URMA,
    };
    for (const auto &[_, hitIndices] : requestHits) {
        for (DiagnosisComponent component : requestComponents) {
            ResolveRequestComponentInterfaces(rules, candidatesByFailure, component, hitIndices);
        }
    }
}

std::vector<std::size_t> DiagnosisResult::FindCommonInterfaceCandidates(
    const std::vector<DiagnosisRule> &rules, const FailureToInterfaces &candidatesByFailure,
    DiagnosisComponent component, const std::vector<std::size_t> &hitIndices,
    std::vector<std::size_t> &componentHitIndices) const
{
    std::vector<std::size_t> commonCandidates;
    bool firstFailure = true;
    for (std::size_t hitIndex : hitIndices) {
        const Hit &hit = hits_[hitIndex];
        if (rules[hit.failureModeIndex].failureMode.component != component) {
            continue;
        }
        componentHitIndices.push_back(hitIndex);
        const auto &candidates = candidatesByFailure[hit.failureModeIndex];
        if (firstFailure) {
            commonCandidates = candidates;
            firstFailure = false;
        } else {
            commonCandidates = SortedIntersection(commonCandidates, candidates);
        }
    }
    return commonCandidates;
}

std::vector<std::size_t> DiagnosisResult::FindCrossComponentAnchors(const std::vector<DiagnosisRule> &rules,
                                                                    DiagnosisComponent component,
                                                                    const std::vector<std::size_t> &hitIndices) const
{
    std::vector<std::size_t> crossAnchors;
    for (std::size_t hitIndex : hitIndices) {
        const std::size_t sourceIndex = hits_[hitIndex].failureModeIndex;
        for (const SchemaEdge &edge : edges_) {
            if (edge.sourceIndex == sourceIndex && edge.type == DiagnosisEdgeType::CROSS_COMPONENT &&
                rules[edge.targetIndex].failureMode.component == component &&
                rules[edge.targetIndex].failureMode.publicApi) {
                crossAnchors.push_back(edge.targetIndex);
            }
        }
    }
    std::sort(crossAnchors.begin(), crossAnchors.end());
    crossAnchors.erase(std::unique(crossAnchors.begin(), crossAnchors.end()), crossAnchors.end());
    return crossAnchors;
}

void DiagnosisResult::ResolveRequestComponentInterfaces(const std::vector<DiagnosisRule> &rules,
                                                        const FailureToInterfaces &candidatesByFailure,
                                                        DiagnosisComponent component,
                                                        const std::vector<std::size_t> &hitIndices)
{
    std::vector<std::size_t> componentHitIndices;
    std::vector<std::size_t> commonCandidates =
        FindCommonInterfaceCandidates(rules, candidatesByFailure, component, hitIndices, componentHitIndices);
    if (componentHitIndices.empty() || commonCandidates.empty()) {
        return;
    }

    const std::vector<std::size_t> crossAnchors = FindCrossComponentAnchors(rules, component, hitIndices);
    bool resolvedByCrossComponent = false;
    if (!crossAnchors.empty()) {
        std::vector<std::size_t> anchoredCandidates = SortedIntersection(commonCandidates, crossAnchors);
        if (!anchoredCandidates.empty()) {
            resolvedByCrossComponent = anchoredCandidates.size() < commonCandidates.size();
            commonCandidates = std::move(anchoredCandidates);
        }
    }
    if (commonCandidates.size() != 1) {
        return;
    }
    for (std::size_t hitIndex : componentHitIndices) {
        Hit &hit = hits_[hitIndex];
        if (hit.interfaceIndex.has_value()) {
            continue;
        }
        hit.interfaceIndex = commonCandidates.front();
        hit.interfaceResolution = resolvedByCrossComponent ? "cross_component" : "thread_chain";
    }
}

Json::Value DiagnosisResult::BuildSchemaNode(const SchemaNode &failureMode) const
{
    Json::Value node(Json::objectValue);
    node["node_id"] = failureMode.id;
    node["node_type"] = failureMode.publicApi ? "interface" : "failure_mode";
    node["component"] = ToString(failureMode.component);
    node["name"] = failureMode.name;
    node["filename"] = failureMode.filename;
    node["function_name"] = failureMode.functionName;
    node["phenomenon"] = failureMode.phenomenon;
    node["cause"] = failureMode.cause;
    node["solution"] = failureMode.solution;
    node["error_code"] = Json::nullValue;
    if (failureMode.errorCode.has_value()) {
        std::visit(
            [&node](const auto &errorCode) {
                using T = std::decay_t<decltype(errorCode)>;
                if constexpr (std::is_same_v<T, std::int64_t>) {
                    node["error_code"] = static_cast<Json::Int64>(errorCode);
                } else {
                    node["error_code"] = errorCode;
                }
            },
            *failureMode.errorCode);
    }
    return node;
}

Json::Value DiagnosisResult::BuildSchemaNodes() const
{
    std::vector<std::size_t> nodeOrder(nodes_.size());
    std::iota(nodeOrder.begin(), nodeOrder.end(), 0);
    std::sort(nodeOrder.begin(), nodeOrder.end(),
              [this](std::size_t left, std::size_t right) { return nodes_[left].id < nodes_[right].id; });

    Json::Value schemaNodes(Json::arrayValue);
    for (std::size_t nodeIndex : nodeOrder) {
        schemaNodes.append(BuildSchemaNode(nodes_[nodeIndex]));
    }
    return schemaNodes;
}

std::vector<std::size_t> DiagnosisResult::BuildSchemaEdgeOrder() const
{
    std::vector<std::size_t> edgeOrder(edges_.size());
    std::iota(edgeOrder.begin(), edgeOrder.end(), 0);
    std::sort(edgeOrder.begin(), edgeOrder.end(), [this](std::size_t leftIndex, std::size_t rightIndex) {
        const SchemaEdge &left = edges_[leftIndex];
        const SchemaEdge &right = edges_[rightIndex];
        return std::make_tuple(nodes_[left.sourceIndex].id, nodes_[left.targetIndex].id, left.type) <
               std::make_tuple(nodes_[right.sourceIndex].id, nodes_[right.targetIndex].id, right.type);
    });
    return edgeOrder;
}

Json::Value DiagnosisResult::BuildSchemaEdges(const std::vector<std::size_t> &edgeOrder) const
{
    Json::Value schemaEdges(Json::arrayValue);
    for (std::size_t edgeIndex : edgeOrder) {
        const SchemaEdge &schemaEdge = edges_[edgeIndex];
        Json::Value edge(Json::objectValue);
        edge["source_node_id"] = nodes_[schemaEdge.sourceIndex].id;
        edge["target_node_id"] = nodes_[schemaEdge.targetIndex].id;
        edge["edge_type"] = ToString(schemaEdge.type);
        schemaEdges.append(std::move(edge));
    }
    return schemaEdges;
}

Json::Value DiagnosisResult::BuildSchemaMappings(const std::vector<std::size_t> &edgeOrder) const
{
    std::vector<std::size_t> outputIndexByStoredIndex(edges_.size());
    for (std::size_t outputIndex = 0; outputIndex < edgeOrder.size(); ++outputIndex) {
        outputIndexByStoredIndex[edgeOrder[outputIndex]] = outputIndex;
    }

    std::vector<std::size_t> mappingOrder(mappings_.size());
    std::iota(mappingOrder.begin(), mappingOrder.end(), 0);
    std::sort(mappingOrder.begin(), mappingOrder.end(), [this](std::size_t left, std::size_t right) {
        return nodes_[mappings_[left].failureModeIndex].id < nodes_[mappings_[right].failureModeIndex].id;
    });
    Json::Value schemaMappings(Json::arrayValue);
    for (std::size_t mappingIndex : mappingOrder) {
        const FailureInterfaceMapping &schemaMapping = mappings_[mappingIndex];
        Json::Value mapping(Json::objectValue);
        mapping["failure_mode_id"] = nodes_[schemaMapping.failureModeIndex].id;
        Json::Value interfaceIds(Json::arrayValue);
        for (std::size_t interfaceIndex : schemaMapping.interfaceIndices) {
            interfaceIds.append(nodes_[interfaceIndex].id);
        }
        mapping["interface_ids"] = std::move(interfaceIds);
        std::vector<std::size_t> subgraphEdgeIndexes;
        subgraphEdgeIndexes.reserve(schemaMapping.subgraphEdgeIndices.size());
        for (std::size_t storedEdgeIndex : schemaMapping.subgraphEdgeIndices) {
            subgraphEdgeIndexes.push_back(outputIndexByStoredIndex[storedEdgeIndex]);
        }
        std::sort(subgraphEdgeIndexes.begin(), subgraphEdgeIndexes.end());
        Json::Value subgraphEdges(Json::arrayValue);
        for (std::size_t outputEdgeIndex : subgraphEdgeIndexes) {
            subgraphEdges.append(static_cast<Json::UInt64>(outputEdgeIndex));
        }
        mapping["subgraph_edge_indexes"] = std::move(subgraphEdges);
        schemaMappings.append(std::move(mapping));
    }
    return schemaMappings;
}

Json::Value DiagnosisResult::BuildSchemaPayload() const
{
    const std::vector<std::size_t> edgeOrder = BuildSchemaEdgeOrder();
    Json::Value schemaPayload(Json::objectValue);
    schemaPayload["format_version"] = SCHEMA_FORMAT_VERSION;
    schemaPayload["nodes"] = BuildSchemaNodes();
    schemaPayload["edges"] = BuildSchemaEdges(edgeOrder);
    schemaPayload["failure_interface_mappings"] = BuildSchemaMappings(edgeOrder);
    return schemaPayload;
}

bool DiagnosisResult::PublishSchema(const std::filesystem::path &outputDirectory, const Json::Value &schemaPayload,
                                    std::string &schemaId) const
{
    schemaId = Sha256Hex(JsonString(schemaPayload, ""));
    Json::Value schema = schemaPayload;
    schema["schema_id"] = schemaId;
    const std::filesystem::path schemaPath = outputDirectory / ("schema_" + schemaId + ".json");
    std::error_code existsError;
    const bool schemaExists = std::filesystem::exists(schemaPath, existsError);
    if (existsError) {
        LOG_ERROR << "failed to inspect schema output: " << existsError.message();
        return false;
    }
    if (!schemaExists && !WriteAtomically(schemaPath, JsonString(schema, "  ") + '\n')) {
        return false;
    }
    return true;
}

Json::Value DiagnosisResult::BuildHit(const Hit &storedHit, std::size_t hitIndex, const std::string &batchId) const
{
    Json::Value hit(Json::objectValue);
    hit["record_type"] = "hit";
    hit["hit_id"] = batchId + ":hit:" + std::to_string(hitIndex);
    hit["failure_mode_id"] = nodes_[storedHit.failureModeIndex].id;
    hit["interface_id"] = Json::nullValue;
    if (storedHit.interfaceIndex.has_value()) {
        hit["interface_id"] = nodes_[*storedHit.interfaceIndex].id;
    }
    hit["interface_resolution"] = storedHit.interfaceResolution;
    hit["timestamp"] = static_cast<Json::Int64>(storedHit.log.timestamp);
    hit["thread_id"] = Json::nullValue;
    hit["trace_id"] = Json::nullValue;
    hit["message"] = storedHit.log.message;
    SetNullableString(hit, "pod_name", storedHit.log.podName);
    SetNullableString(hit, "pod_ip", storedHit.log.podIp);
    SetNullableString(hit, "component", ToString(nodes_[storedHit.failureModeIndex].component));
    SetNullableString(hit, "filename", storedHit.log.filename);
    SetNullableString(hit, "function_name", storedHit.log.functionName);
    hit["line_number"] = storedHit.log.lineNo;
    if (storedHit.log.threadId.has_value()) {
        hit["thread_id"] = *storedHit.log.threadId;
    }
    if (storedHit.log.traceId.has_value() && !storedHit.log.traceId->empty()) {
        hit["trace_id"] = *storedHit.log.traceId;
    }
    return hit;
}

std::string DiagnosisResult::BuildBatchContent(const std::string &taskId, const std::string &batchId,
                                               const std::string &schemaId, std::int64_t createdAtTimestamp) const
{
    std::int64_t batchStartTimestamp = startTimestamp_;
    std::int64_t batchEndTimestamp = endTimestamp_;
    if (hits_.empty()) {
        batchStartTimestamp = createdAtTimestamp;
        batchEndTimestamp = (createdAtTimestamp / MICROSECONDS_PER_SECOND + 1) * MICROSECONDS_PER_SECOND;
    }
    Json::Value batch(Json::objectValue);
    batch["record_type"] = "batch";
    batch["format_version"] = BATCH_FORMAT_VERSION;
    batch["task_id"] = taskId;
    batch["batch_id"] = batchId;
    batch["schema_id"] = schemaId;
    batch["created_at_timestamp"] = static_cast<Json::Int64>(createdAtTimestamp);
    batch["start_timestamp"] = static_cast<Json::Int64>(batchStartTimestamp);
    batch["end_timestamp"] = static_cast<Json::Int64>(batchEndTimestamp);
    batch["hit_count"] = static_cast<Json::UInt64>(hits_.size());

    std::string batchContent = JsonString(batch, "") + '\n';
    for (std::size_t hitIndex = 0; hitIndex < hits_.size(); ++hitIndex) {
        batchContent += JsonString(BuildHit(hits_[hitIndex], hitIndex, batchId), "") + '\n';
    }
    return batchContent;
}

bool DiagnosisResult::Dump(const std::filesystem::path &outputDirectory, const std::string &taskId) const
{
    std::error_code directoryError;
    std::filesystem::create_directories(outputDirectory, directoryError);
    if (directoryError) {
        LOG_ERROR << "failed to create diagnosis output directory " << outputDirectory.string() << ": "
                  << directoryError.message();
        return false;
    }
    const Json::Value schemaPayload = BuildSchemaPayload();
    std::string schemaId;
    if (!PublishSchema(outputDirectory, schemaPayload, schemaId)) {
        return false;
    }
    const std::int64_t createdAtTimestamp =
        std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::system_clock::now().time_since_epoch())
            .count();
    const std::optional<std::string> batchId = GenerateUuidV7(createdAtTimestamp);
    if (!batchId.has_value()) {
        return false;
    }
    const std::string batchContent = BuildBatchContent(taskId, *batchId, schemaId, createdAtTimestamp);
    const std::filesystem::path batchPath = outputDirectory / ("batch_" + taskId + ".jsonl");
    if (!WriteAtomically(batchPath, batchContent)) {
        return false;
    }
    LOG_INFO << "diagnosis schema " << schemaId << " and batch " << *batchId << " published to "
             << outputDirectory.string();
    return true;
}

} // namespace brpc
