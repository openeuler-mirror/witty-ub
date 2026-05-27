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

#define MODULE_NAME "LOG"

#include "log_view.h"

#include <sys/stat.h>

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <memory>
#include <optional>
#include <string>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "logger.h"

namespace failure::log {

constexpr const char *LOG_VIEW_FILE = "/var/witty-ub/log-view.json";
constexpr mode_t LOG_VIEW_FILE_PERM_640 = 0640;

namespace {
constexpr char EDGE_KEY_SEP = '\n';
constexpr char NODE_KEY_SEP = '\n';
const std::string NULL_ERROR_CODE_KEY = "";
using FuncNameToIndices = std::unordered_map<std::string, std::vector<size_t>>;
using FuncErrorCodes = std::unordered_map<std::string, std::unordered_set<std::string>>;

struct NodeHitStat {
    const graph::FuncNode *node{nullptr};
    std::string viewId;
    std::string errorCode;
    int hitCount{0};
};

using MergedNodeMap = std::unordered_map<std::string, NodeHitStat>;

struct ViewAgg {
    MergedNodeMap mergedNodeMap;
    std::unordered_map<std::string, int> edgeHitCount;
};

struct RemoteJettyResourceAgg {
    std::unordered_map<std::string, int> remoteEidHitCount;
};

struct JettyResourceAgg {
    std::unordered_map<std::string, RemoteJettyResourceAgg> remoteJettyAggById;
};

struct EidResourceAgg {
    int hitCount{0};
    std::unordered_map<std::string, JettyResourceAgg> jettyAggById;
};

struct TidResourceAgg {
    int hitCount{0};
    std::unordered_map<std::string, EidResourceAgg> eidAggById;
};

struct ResourceViewAgg {
    int hitCount{0};
    std::unordered_map<std::string, TidResourceAgg> tidAggById;
};

struct EdgeHitStat {
    std::string src;
    std::string dst;
    int hitCount;
    double ratio;
};

void InitRoot(Json::Value &root)
{
    root = Json::Value(Json::objectValue);
    root["callstack_views"] = Json::Value(Json::arrayValue);
    root["resource_views"] = Json::Value(Json::arrayValue);
}

std::string BuildNodeKey(const std::string &funcName, const std::string &errorCode)
{
    std::string key;
    key.reserve(funcName.size() + 1 + errorCode.size());
    key.append(funcName);
    key.push_back(NODE_KEY_SEP);
    key.append(errorCode);
    return key;
}

std::string BuildNodeViewId(const std::string &funcName, const std::string &errorCode)
{
    if (errorCode.empty()) {
        return funcName;
    }
    return funcName + "#" + errorCode;
}

std::string BuildEdgeKey(const std::string &src, const std::string &dst)
{
    std::string key;
    key.reserve(src.size() + 1 + dst.size());
    key.append(src);
    key.push_back(EDGE_KEY_SEP);
    key.append(dst);
    return key;
}

std::pair<std::string, std::string> ParseEdgeKey(const std::string &key)
{
    const auto pos = key.find(EDGE_KEY_SEP);
    if (pos == std::string::npos) {
        return {"", ""};
    }
    return {key.substr(0, pos), key.substr(pos + 1)};
}

std::string GetEventErrorCode(const FailureEvent *event)
{
    if (event == nullptr) {
        return NULL_ERROR_CODE_KEY;
    }
    static const std::vector<std::string> errorCodeKeys = {"error_code", "errorCode",   "err_code",    "errno",
                                                           "ret_code",   "return_code", "status_code", "code"};
    for (const std::string &key : errorCodeKeys) {
        auto it = event->attributes.find(key);
        if (it != event->attributes.end() && !it->second.empty()) {
            return it->second;
        }
    }
    return NULL_ERROR_CODE_KEY;
}

FuncNameToIndices BuildNameToIndices(const graph::CallGraph &graph)
{
    FuncNameToIndices nameToIndices;
    nameToIndices.reserve(graph.nodes.size());
    for (size_t i = 0; i < graph.nodes.size(); ++i) {
        nameToIndices[graph.nodes[i].name].push_back(i);
    }
    return nameToIndices;
}

FuncErrorCodes CollectFuncErrorCodes(const FailureMetadata &meta)
{
    FuncErrorCodes funcErrorCodes;
    if (!meta.funcName.empty()) {
        funcErrorCodes[meta.funcName].insert(NULL_ERROR_CODE_KEY);
    }
    for (const FailureEvent *event : meta.events) {
        if (event == nullptr) {
            continue;
        }
        auto it = event->attributes.find("function_name");
        if (it != event->attributes.end() && !it->second.empty()) {
            auto &errorCodes = funcErrorCodes[it->second];
            const std::string errorCode = GetEventErrorCode(event);
            errorCodes.insert(errorCode);
            if (it->second == meta.funcName && !errorCode.empty()) {
                errorCodes.erase(NULL_ERROR_CODE_KEY);
            }
        }
    }
    return funcErrorCodes;
}

std::string ResolveTopFunction(const FailureMetadata &meta, const graph::CallGraph &graph)
{
    FuncErrorCodes funcErrorCodes = CollectFuncErrorCodes(meta);
    std::unordered_set<std::string> funcNames;
    funcNames.reserve(funcErrorCodes.size());
    for (const auto &[funcName, _] : funcErrorCodes) {
        if (graph.nodeIndex.find(funcName) != graph.nodeIndex.end()) {
            funcNames.insert(funcName);
        }
    }
    if (funcNames.empty()) {
        return meta.funcName;
    }

    std::vector<std::string> topFunctions;
    topFunctions.reserve(funcNames.size());
    for (const std::string &funcName : funcNames) {
        const auto nodeIt = graph.nodeIndex.find(funcName);
        if (nodeIt == graph.nodeIndex.end()) {
            continue;
        }
        bool hasUpstreamInView = false;
        for (size_t upstreamIdx : graph.upstreamEdges[nodeIt->second]) {
            if (upstreamIdx < graph.nodes.size() && funcNames.find(graph.nodes[upstreamIdx].name) != funcNames.end()) {
                hasUpstreamInView = true;
                break;
            }
        }
        if (!hasUpstreamInView) {
            topFunctions.push_back(funcName);
        }
    }
    if (topFunctions.empty()) {
        return meta.funcName;
    }
    if (std::find(topFunctions.begin(), topFunctions.end(), meta.funcName) != topFunctions.end()) {
        return meta.funcName;
    }
    std::sort(topFunctions.begin(), topFunctions.end());
    return topFunctions.front();
}

void MergeMetadataNodes(const graph::CallGraph &graph, const FuncErrorCodes &funcErrorCodes,
                        const FuncNameToIndices &nameToIndices, MergedNodeMap &mergedNodeMap,
                        std::unordered_map<std::string, std::vector<std::string>> &funcNameToViewIds)
{
    for (const auto &[funcName, errorCodes] : funcErrorCodes) {
        auto nameIt = nameToIndices.find(funcName);
        if (nameIt == nameToIndices.end()) {
            continue;
        }
        for (size_t idx : nameIt->second) {
            const graph::FuncNode &node = graph.nodes[idx];
            for (const std::string &errorCode : errorCodes) {
                std::string nodeKey = BuildNodeKey(node.name, errorCode);
                std::string viewId = BuildNodeViewId(node.name, errorCode);
                auto [it, _] = mergedNodeMap.emplace(nodeKey, NodeHitStat{&node, viewId, errorCode, 0});
                ++it->second.hitCount;
                funcNameToViewIds[node.name].push_back(viewId);
            }
        }
    }
    for (auto &[_, viewIds] : funcNameToViewIds) {
        std::sort(viewIds.begin(), viewIds.end());
        viewIds.erase(std::unique(viewIds.begin(), viewIds.end()), viewIds.end());
    }
}

void MergeMetadataEdges(const graph::CallGraph &graph,
                        const std::unordered_map<std::string, std::vector<std::string>> &funcNameToViewIds,
                        std::unordered_map<std::string, int> &edgeHitCount)
{
    std::unordered_set<std::string> metadataEdgeKeys;
    for (const graph::CallEdge &edge : graph.edges) {
        auto srcIt = funcNameToViewIds.find(edge.src);
        auto dstIt = funcNameToViewIds.find(edge.dst);
        if (srcIt == funcNameToViewIds.end() || dstIt == funcNameToViewIds.end()) {
            continue;
        }
        for (const std::string &srcViewId : srcIt->second) {
            for (const std::string &dstViewId : dstIt->second) {
                metadataEdgeKeys.insert(BuildEdgeKey(srcViewId, dstViewId));
            }
        }
    }
    for (const std::string &edgeKey : metadataEdgeKeys) {
        ++edgeHitCount[edgeKey];
    }
}

void MergeMetadataView(const FailureMetadata &meta, const graph::CallGraph &graph,
                       const FuncNameToIndices &nameToIndices, MergedNodeMap &mergedNodeMap,
                       std::unordered_map<std::string, int> &edgeHitCount)
{
    auto funcErrorCodes = CollectFuncErrorCodes(meta);
    std::unordered_map<std::string, std::vector<std::string>> funcNameToViewIds;
    MergeMetadataNodes(graph, funcErrorCodes, nameToIndices, mergedNodeMap, funcNameToViewIds);
    MergeMetadataEdges(graph, funcNameToViewIds, edgeHitCount);
}

std::vector<NodeHitStat> CollectSortedMergedNodes(const MergedNodeMap &mergedNodeMap)
{
    std::vector<NodeHitStat> mergedNodes;
    mergedNodes.reserve(mergedNodeMap.size());
    for (const auto &[_, stat] : mergedNodeMap) {
        if (stat.node != nullptr) {
            mergedNodes.push_back(stat);
        }
    }
    std::sort(mergedNodes.begin(), mergedNodes.end(),
              [](const NodeHitStat &a, const NodeHitStat &b) { return a.viewId < b.viewId; });
    return mergedNodes;
}

void AppendMergedNodes(Json::Value &view, const MergedNodeMap &mergedNodeMap)
{
    auto mergedNodes = CollectSortedMergedNodes(mergedNodeMap);
    for (const NodeHitStat &stat : mergedNodes) {
        const graph::FuncNode *node = stat.node;
        Json::Value nodeJson(Json::objectValue);
        nodeJson["id"] = stat.viewId;
        nodeJson["callstack_name"] = node->name;
        nodeJson["function_name"] = node->name;
        nodeJson["component"] = node->component;
        nodeJson["error_code"] = stat.errorCode.empty() ? Json::Value(Json::nullValue) : Json::Value(stat.errorCode);
        nodeJson["hit_count"] = stat.hitCount;
        view["nodes"].append(nodeJson);
    }
}

std::unordered_map<std::string, int> BuildDownstreamTotalHitCountBySrc(
    const std::unordered_map<std::string, int> &edgeHitCount)
{
    std::unordered_map<std::string, int> totals;
    for (const auto &[key, hitCount] : edgeHitCount) {
        auto [src, dst] = ParseEdgeKey(key);
        if (!src.empty() && !dst.empty()) {
            totals[src] += hitCount;
        }
    }
    return totals;
}

std::vector<EdgeHitStat> BuildSortedMergedEdges(
    const std::unordered_map<std::string, int> &edgeHitCount,
    const std::unordered_map<std::string, int> &downstreamTotalHitCountBySrc)
{
    std::vector<EdgeHitStat> mergedEdges;
    mergedEdges.reserve(edgeHitCount.size());
    for (const auto &[key, hitCount] : edgeHitCount) {
        auto [src, dst] = ParseEdgeKey(key);
        if (src.empty() || dst.empty()) {
            continue;
        }
        double ratio = 0.0;
        auto totalIt = downstreamTotalHitCountBySrc.find(src);
        if (totalIt != downstreamTotalHitCountBySrc.end() && totalIt->second > 0) {
            ratio = static_cast<double>(hitCount) / static_cast<double>(totalIt->second);
        }
        mergedEdges.push_back({src, dst, hitCount, ratio});
    }
    std::sort(mergedEdges.begin(), mergedEdges.end(), [](const EdgeHitStat &a, const EdgeHitStat &b) {
        return std::tie(a.src, a.dst) < std::tie(b.src, b.dst);
    });
    return mergedEdges;
}

void AppendMergedEdges(Json::Value &view, const std::vector<EdgeHitStat> &mergedEdges)
{
    for (const EdgeHitStat &edge : mergedEdges) {
        Json::Value edgeJson(Json::objectValue);
        edgeJson["src"] = edge.src;
        edgeJson["dst"] = edge.dst;
        edgeJson["hit_count"] = edge.hitCount;
        edgeJson["ratio"] = edge.ratio;
        view["edges"].append(edgeJson);
    }
}

Json::Value BuildTopFunctionView(const std::string &topFunction, const ViewAgg &agg)
{
    Json::Value view(Json::objectValue);
    view["top_function"] = topFunction.empty() ? Json::Value(Json::nullValue) : Json::Value(topFunction);
    view["nodes"] = Json::Value(Json::arrayValue);
    view["edges"] = Json::Value(Json::arrayValue);
    AppendMergedNodes(view, agg.mergedNodeMap);
    auto downstreamTotalHitCountBySrc = BuildDownstreamTotalHitCountBySrc(agg.edgeHitCount);
    auto mergedEdges = BuildSortedMergedEdges(agg.edgeHitCount, downstreamTotalHitCountBySrc);
    AppendMergedEdges(view, mergedEdges);
    return view;
}

std::string OptionalResourceId(const std::optional<std::string> &value)
{
    return value.value_or("");
}

Json::Value ResourceIdToJson(const std::string &value)
{
    return value.empty() ? Json::Value(Json::nullValue) : Json::Value(value);
}

std::vector<std::string> CollectSortedKeys(const std::unordered_map<std::string, int> &values)
{
    std::vector<std::string> keys;
    keys.reserve(values.size());
    for (const auto &[key, _] : values) {
        keys.push_back(key);
    }
    std::sort(keys.begin(), keys.end());
    return keys;
}

template <typename T>
std::vector<std::string> CollectSortedKeys(const std::unordered_map<std::string, T> &values)
{
    std::vector<std::string> keys;
    keys.reserve(values.size());
    for (const auto &[key, _] : values) {
        keys.push_back(key);
    }
    std::sort(keys.begin(), keys.end());
    return keys;
}

double CalcRatio(int hitCount, int totalHitCount)
{
    if (totalHitCount <= 0) {
        return 0.0;
    }
    return static_cast<double>(hitCount) / static_cast<double>(totalHitCount);
}

void MergeResourceMetadata(const FailureMetadata &meta, ResourceViewAgg &agg)
{
    ++agg.hitCount;
    TidResourceAgg &tidAgg = agg.tidAggById[meta.threadId];
    ++tidAgg.hitCount;
    EidResourceAgg &eidAgg = tidAgg.eidAggById[meta.localEid];
    ++eidAgg.hitCount;

    JettyResourceAgg &jettyAgg = eidAgg.jettyAggById[meta.localJettyId];
    RemoteJettyResourceAgg &remoteJettyAgg = jettyAgg.remoteJettyAggById[OptionalResourceId(meta.remoteJettyId)];
    ++remoteJettyAgg.remoteEidHitCount[OptionalResourceId(meta.remoteEid)];
}

Json::Value BuildRemoteEids(const RemoteJettyResourceAgg &remoteJettyAgg)
{
    Json::Value remoteEids(Json::arrayValue);
    for (const std::string &remoteEid : CollectSortedKeys(remoteJettyAgg.remoteEidHitCount)) {
        Json::Value remoteEidJson(Json::objectValue);
        remoteEidJson["remote_eid"] = ResourceIdToJson(remoteEid);
        remoteEids.append(remoteEidJson);
    }
    return remoteEids;
}

Json::Value BuildRemoteJetties(const JettyResourceAgg &jettyAgg)
{
    Json::Value remoteJetties(Json::arrayValue);
    for (const std::string &remoteJettyId : CollectSortedKeys(jettyAgg.remoteJettyAggById)) {
        Json::Value remoteJettyJson(Json::objectValue);
        remoteJettyJson["remote_jetty_id"] = ResourceIdToJson(remoteJettyId);
        remoteJettyJson["remote_eids"] = BuildRemoteEids(jettyAgg.remoteJettyAggById.at(remoteJettyId));
        remoteJetties.append(remoteJettyJson);
    }
    return remoteJetties;
}

Json::Value BuildJetties(const EidResourceAgg &eidAgg)
{
    Json::Value jetties(Json::arrayValue);
    for (const std::string &jettyId : CollectSortedKeys(eidAgg.jettyAggById)) {
        Json::Value jettyJson(Json::objectValue);
        jettyJson["jetty_id"] = ResourceIdToJson(jettyId);
        jettyJson["remote_jetty_ids"] = BuildRemoteJetties(eidAgg.jettyAggById.at(jettyId));
        jetties.append(jettyJson);
    }
    return jetties;
}

Json::Value BuildEids(const TidResourceAgg &tidAgg)
{
    Json::Value eids(Json::arrayValue);
    for (const std::string &eid : CollectSortedKeys(tidAgg.eidAggById)) {
        const EidResourceAgg &eidAgg = tidAgg.eidAggById.at(eid);
        Json::Value eidJson(Json::objectValue);
        eidJson["eid"] = ResourceIdToJson(eid);
        eidJson["hit_count"] = eidAgg.hitCount;
        eidJson["ratio"] = CalcRatio(eidAgg.hitCount, tidAgg.hitCount);
        eidJson["jetty_ids"] = BuildJetties(eidAgg);
        eids.append(eidJson);
    }
    return eids;
}

Json::Value BuildTids(const ResourceViewAgg &agg)
{
    Json::Value tids(Json::arrayValue);
    for (const std::string &tid : CollectSortedKeys(agg.tidAggById)) {
        const TidResourceAgg &tidAgg = agg.tidAggById.at(tid);
        Json::Value tidJson(Json::objectValue);
        tidJson["tid"] = ResourceIdToJson(tid);
        tidJson["hit_count"] = tidAgg.hitCount;
        tidJson["ratio"] = CalcRatio(tidAgg.hitCount, agg.hitCount);
        tidJson["eids"] = BuildEids(tidAgg);
        tids.append(tidJson);
    }
    return tids;
}

Json::Value BuildTopFunctionResourceView(const std::string &topFunction, const ResourceViewAgg &agg)
{
    Json::Value view(Json::objectValue);
    view["top_function"] = topFunction.empty() ? Json::Value(Json::nullValue) : Json::Value(topFunction);
    view["tids"] = BuildTids(agg);
    return view;
}
} // namespace

RackResult LogView::Build(const std::vector<FailureMetadata> &metadata, const graph::CallGraph &graph)
{
    InitRoot(root_);
    std::unordered_map<std::string, ViewAgg> viewAggByTopFunc;
    std::unordered_map<std::string, ResourceViewAgg> resourceViewAggByTopFunc;
    FuncNameToIndices nameToIndices = BuildNameToIndices(graph);

    for (const FailureMetadata &meta : metadata) {
        const std::string topFunction = ResolveTopFunction(meta, graph);
        ViewAgg &agg = viewAggByTopFunc[topFunction];
        MergeMetadataView(meta, graph, nameToIndices, agg.mergedNodeMap, agg.edgeHitCount);
        MergeResourceMetadata(meta, resourceViewAggByTopFunc[topFunction]);
    }

    std::vector<std::string> sortedTopFunctions;
    sortedTopFunctions.reserve(viewAggByTopFunc.size());
    for (const auto &[topFunction, _] : resourceViewAggByTopFunc) {
        sortedTopFunctions.push_back(topFunction);
    }
    std::sort(sortedTopFunctions.begin(), sortedTopFunctions.end());
    for (const std::string &topFunction : sortedTopFunctions) {
        root_["callstack_views"].append(BuildTopFunctionView(topFunction, viewAggByTopFunc.at(topFunction)));
        root_["resource_views"].append(
            BuildTopFunctionResourceView(topFunction, resourceViewAggByTopFunc.at(topFunction)));
    }

    return RACK_OK;
}

RackResult LogView::Dump() const
{
    std::filesystem::path outFile = LOG_VIEW_FILE;
    std::error_code ec;
    std::filesystem::create_directories(outFile.parent_path(), ec);
    if (ec) {
        LOG_ERROR << "failed to prepare output directory: " << outFile.parent_path() << ", error: " << ec.message();
        return RACK_FAIL;
    }

    Json::StreamWriterBuilder builder;
    builder["indentation"] = "  ";
    std::unique_ptr<Json::StreamWriter> writer(builder.newStreamWriter());

    std::ofstream ofs(LOG_VIEW_FILE, std::ios::out | std::ios::trunc);
    if (!ofs.is_open()) {
        LOG_ERROR << "failed to open output file: " << LOG_VIEW_FILE;
        return RACK_FAIL;
    }
    writer->write(root_, &ofs);
    ofs.flush();
    ofs.close();

    if (::chmod(LOG_VIEW_FILE, LOG_VIEW_FILE_PERM_640) != 0) {
        LOG_ERROR << "failed to set file mode 0640 for output file: " << LOG_VIEW_FILE;
        return RACK_FAIL;
    }

    return RACK_OK;
}
} // namespace failure::log
