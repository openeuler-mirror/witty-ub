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

#include "failure_mode_view.h"

#include <algorithm>
#include <filesystem>

#include <sys/stat.h>

#include <json/json.h>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <utility>
#include <vector>

#include "failure_def.h"
#include "logger.h"

namespace diag {
constexpr const char *HTML_OUTPUT_FILENAME = "failure-mode-view-vis.html";
constexpr const char *DEFAULT_OUTPUT_DIR = "/var/witty-ub";
constexpr const char *VIEW_VIS_RUNTIME_RESOURCE_DIR = "/var/witty-ub/data/view-vis";
constexpr const char *VIEW_VIS_SOURCE_RESOURCE_DIR = "data/view-vis";
constexpr const char *HTML_TEMPLATE_NAME = "failure_mode_view.html";
constexpr const char *CSS_RESOURCE_NAME = "failure_mode_view.css";
constexpr const char *JS_RESOURCE_NAME = "failure_mode_view.js";
constexpr const char *DATA_PLACEHOLDER = "__FAILURE_MODE_VIEW_DATA__";
constexpr const char *CSS_PLACEHOLDER = "__FAILURE_MODE_VIEW_CSS__";
constexpr const char *JS_PLACEHOLDER = "__FAILURE_MODE_VIEW_JS__";
constexpr mode_t OUTPUT_FILE_PERM_640 = 0640;
constexpr const int MICROSECONDS_UNIT = 1000000;
constexpr const int MICROSECONDS_LEN = 6;

using TraceView = std::pair<std::string, const std::vector<std::shared_ptr<FailureLogInfo>> *>;

std::string FormatLogTime(int64_t timestamp)
{
    auto datetime = failure::TimestampToDatetimeStr(timestamp, "iso8601");
    if (!datetime.has_value()) {
        return std::to_string(timestamp);
    }
    int64_t microseconds = timestamp % MICROSECONDS_UNIT;
    if (microseconds < 0) {
        microseconds += MICROSECONDS_UNIT;
    }
    if (microseconds == 0) {
        return *datetime;
    }
    std::ostringstream oss;
    oss << *datetime << "." << std::setw(MICROSECONDS_LEN) << std::setfill('0') << microseconds;
    return oss.str();
}

Json::Value LogInfoToJson(const std::shared_ptr<FailureLogInfo> logInfo)
{
    Json::Value logJson(Json::objectValue);
    logJson["time"] = FormatLogTime(logInfo->timestamp);
    logJson["timestamp"] = Json::Int64(logInfo->timestamp);
    logJson["failure_mode_id"] = Json::Value(Json::arrayValue);
    for (const std::string &failureModeId : logInfo->failureModeIds) {
        logJson["failure_mode_id"].append(failureModeId);
    }
    logJson["filename"] = logInfo->filename;
    logJson["line_no"] = logInfo->lineNo;
    logJson["pod_name"] = logInfo->podName;
    logJson["pid"] = logInfo->pid;
    logJson["tid"] = logInfo->tid;
    logJson["trace_id"] = logInfo->traceId;
    logJson["cluster_name"] = logInfo->clusterName;
    auto logInfoTmp = logInfo;
    if (auto accessInfo = std::dynamic_pointer_cast<FailureLogInfoAccess>(logInfoTmp)) {
        logJson["status_code"] = accessInfo->statusCode;
        logJson["action"] = accessInfo->action;
        logJson["cost"] = accessInfo->cost;
        logJson["data_size"] = accessInfo->dataSize;
        logJson["req_msg"] = accessInfo->reqMsg;
        logJson["resp_msg"] = accessInfo->respMsg;
    } else if (auto logInfoRuntime = std::dynamic_pointer_cast<FailureLogInfoRuntime>(logInfoTmp)) {
        logJson["message"] = logInfoRuntime->message;
    }
    return logJson;
}

Json::Value TraceToJson(const std::string &traceId, const std::vector<std::shared_ptr<FailureLogInfo>> &trace)
{
    Json::Value traceJson(Json::objectValue);
    traceJson["trace_id"] = traceId;
    traceJson["logs"] = Json::Value(Json::arrayValue);

    std::vector<std::shared_ptr<FailureLogInfo>> logInfos;
    logInfos.reserve(trace.size());
    for (const auto &logInfo : trace) {
        logInfos.push_back(logInfo);
    }
    std::sort(logInfos.begin(), logInfos.end(),
              [](const auto &left, const auto &right) { return left->timestamp > right->timestamp; });

    if (!logInfos.empty()) {
        int64_t startTime = logInfos.front()->timestamp;
        int64_t endTime = logInfos.front()->timestamp;
        for (const auto &logInfo : logInfos) {
            startTime = std::min(startTime, logInfo->timestamp);
            endTime = std::max(endTime, logInfo->timestamp);
        }
        traceJson["start_time"] = FormatLogTime(startTime);
        traceJson["end_time"] = FormatLogTime(endTime);
        traceJson["duration_us"] = Json::Int64(endTime - startTime);
        traceJson["mode_count"] = static_cast<Json::UInt64>(logInfos.size());
    } else {
        traceJson["start_time"] = "";
        traceJson["end_time"] = "";
        traceJson["duration_us"] = Json::Int64(0);
        traceJson["mode_count"] = Json::UInt64(0);
    }

    for (const auto &logInfo : logInfos) {
        traceJson["logs"].append(LogInfoToJson(logInfo));
    }
    return traceJson;
}

std::string JsonToString(const Json::Value &root)
{
    Json::StreamWriterBuilder builder;
    builder["indentation"] = "  ";
    return Json::writeString(builder, root);
}

std::string EscapeJsonForScript(const std::string &json)
{
    std::string escaped;
    escaped.reserve(json.size());
    for (size_t i = 0; i < json.size(); ++i) {
        if (json[i] == '<' && i + 1 < json.size() && json[i + 1] == '/') {
            escaped.append("<\\");
        } else {
            escaped.push_back(json[i]);
        }
    }
    return escaped;
}

bool ReadTextFile(const std::filesystem::path &path, std::string &content)
{
    std::ifstream ifs(path);
    if (!ifs.is_open()) {
        return false;
    }
    std::ostringstream oss;
    oss << ifs.rdbuf();
    content = oss.str();
    return ifs.good() || ifs.eof();
}

RackResult ReadResourceFile(const std::string &fileName, std::string &content)
{
    std::filesystem::path sourceResourcePath = VIEW_VIS_SOURCE_RESOURCE_DIR;
    sourceResourcePath.append(fileName);
    std::filesystem::path relativeResourcePath = std::filesystem::path(__FILE__).parent_path();
    relativeResourcePath.append("../../data/view-vis");
    relativeResourcePath.append(fileName);
    std::filesystem::path runtimeResourcePath = VIEW_VIS_RUNTIME_RESOURCE_DIR;
    runtimeResourcePath.append(fileName);

    const std::vector<std::filesystem::path> candidates = {
        sourceResourcePath,
        relativeResourcePath,
        runtimeResourcePath,
    };

    for (const std::filesystem::path &candidate : candidates) {
        if (ReadTextFile(candidate, content)) {
            return RACK_OK;
        }
    }

    LOG_ERROR << "failed to read failure mode view resource: " << fileName;
    return RACK_FAIL;
}

bool ReplaceFirst(std::string &content, const std::string &placeholder, const std::string &replacement)
{
    const size_t pos = content.find(placeholder);
    if (pos == std::string::npos) {
        return false;
    }
    content.replace(pos, placeholder.size(), replacement);
    return true;
}

bool CompareFailureModeViewNode(const FailureModeViewNode *left, const FailureModeViewNode *right)
{
    if (left->GetData().id != right->GetData().id) {
        return left->GetData().id < right->GetData().id;
    }
    return left->GetData().name < right->GetData().name;
}

int64_t GetLatestTraceTimestamp(const std::vector<std::shared_ptr<FailureLogInfo>> &trace)
{
    int64_t latest = 0;
    for (const auto &logInfo : trace) {
        latest = std::max(latest, logInfo->timestamp);
    }
    return latest;
}

bool CompareTraceView(const TraceView &left, const TraceView &right)
{
    int64_t leftTime = GetLatestTraceTimestamp(*left.second);
    int64_t rightTime = GetLatestTraceTimestamp(*right.second);
    if (leftTime != rightTime) {
        return leftTime > rightTime;
    }
    return left.first < right.first;
}

Json::Value NodeToJson(const FailureModeViewNode &node)
{
    Json::Value nodeJson(Json::objectValue);
    nodeJson["id"] = node.GetData().id;
    nodeJson["name"] = node.GetData().name;
    nodeJson["cause"] = node.GetData().cause;
    nodeJson["suggestion"] = node.GetData().suggestion;
    nodeJson["validation"] = node.GetData().validation;
    nodeJson["hit_count"] = node.GetData().hitCount;

    nodeJson["log_info"] = Json::objectValue;
    for (const auto &[traceId, logInfo] : node.GetData().traceIdToFailureLogInfo) {
        nodeJson["log_info"][traceId] = LogInfoToJson(logInfo);
    }

    nodeJson["children"] = Json::Value(Json::arrayValue);
    std::vector<const FailureModeViewNode *> children;
    children.reserve(node.GetSubNodes().size());
    for (const FailureModeViewNode &child : node.GetSubNodes()) {
        children.push_back(&child);
    }
    std::sort(children.begin(), children.end(), CompareFailureModeViewNode);
    for (const FailureModeViewNode *child : children) {
        nodeJson["children"].append(NodeToJson(*child));
    }

    return nodeJson;
}

Json::Value BuildRootJson(
    const std::vector<FailureModeViewNode> &roots,
    const std::unordered_map<std::string, std::vector<std::shared_ptr<FailureLogInfo>>> &traceIdToFailureLogInfos)
{
    Json::Value root(Json::objectValue);
    root["trees"] = Json::Value(Json::arrayValue);
    root["traces"] = Json::Value(Json::arrayValue);

    std::vector<const FailureModeViewNode *> sortedRoots;
    sortedRoots.reserve(roots.size());
    for (const FailureModeViewNode &node : roots) {
        sortedRoots.push_back(&node);
    }
    std::sort(sortedRoots.begin(), sortedRoots.end(), CompareFailureModeViewNode);
    for (const FailureModeViewNode *node : sortedRoots) {
        root["trees"].append(NodeToJson(*node));
    }

    std::vector<TraceView> sortedTraces;
    sortedTraces.reserve(traceIdToFailureLogInfos.size());
    for (const auto &[traceId, trace] : traceIdToFailureLogInfos) {
        sortedTraces.emplace_back(traceId, &trace);
    }
    std::sort(sortedTraces.begin(), sortedTraces.end(), CompareTraceView);
    for (const auto &[traceId, trace] : sortedTraces) {
        root["traces"].append(TraceToJson(traceId, *trace));
    }
    return root;
}

std::string BuildHtml(const Json::Value &root)
{
    std::string htmlTemplate;
    if (ReadResourceFile(HTML_TEMPLATE_NAME, htmlTemplate) != RACK_OK) {
        return "";
    }
    std::string css;
    if (ReadResourceFile(CSS_RESOURCE_NAME, css) != RACK_OK) {
        return "";
    }
    std::string js;
    if (ReadResourceFile(JS_RESOURCE_NAME, js) != RACK_OK) {
        return "";
    }

    if (!ReplaceFirst(htmlTemplate, DATA_PLACEHOLDER, EscapeJsonForScript(JsonToString(root)))) {
        LOG_ERROR << "failure mode view template missing data placeholder: " << DATA_PLACEHOLDER;
        return "";
    }
    if (!ReplaceFirst(htmlTemplate, CSS_PLACEHOLDER, css)) {
        LOG_ERROR << "failure mode view template missing css placeholder: " << CSS_PLACEHOLDER;
        return "";
    }
    if (!ReplaceFirst(htmlTemplate, JS_PLACEHOLDER, js)) {
        LOG_ERROR << "failure mode view template missing js placeholder: " << JS_PLACEHOLDER;
        return "";
    }
    return htmlTemplate;
}

RackResult WriteHtml(const std::string &html, const std::string &outputDir)
{
    std::filesystem::path outputPath =
        std::filesystem::path(outputDir.empty() ? DEFAULT_OUTPUT_DIR : outputDir) / HTML_OUTPUT_FILENAME;
    std::error_code ec;
    std::filesystem::create_directories(outputPath.parent_path(), ec);
    if (ec) {
        LOG_ERROR << "failed to create failure mode view output directory: " << outputPath.parent_path()
                  << ", error: " << ec.message();
        return RACK_FAIL;
    }

    std::ofstream ofs(outputPath, std::ios::out | std::ios::trunc);
    if (!ofs.is_open()) {
        LOG_ERROR << "failed to open failure mode view html: " << outputPath;
        return RACK_FAIL;
    }
    ofs << html;
    ofs.flush();
    ofs.close();
    if (!ofs.good()) {
        LOG_ERROR << "failed to write failure mode view html: " << outputPath;
        return RACK_FAIL;
    }
    if (::chmod(outputPath.c_str(), OUTPUT_FILE_PERM_640) != 0) {
        LOG_ERROR << "failed to set file mode 0640 for failure mode view html: " << outputPath;
        return RACK_FAIL;
    }
    return RACK_OK;
}

FailureModeViewNodeData::FailureModeViewNodeData(const FailureModeController &controller)
    : id(controller.GetFailureMode()->GetId()),
      name(controller.GetFailureMode()->GetName()),
      cause(controller.GetFailureMode()->GetRootCauseDesc()),
      suggestion(controller.GetFailureMode()->GetFixSuggDesc()),
      validation(controller.GetFailureMode()->GetValidationMethodDesc()),
      hitCount(controller.GetHitCount()),
      traceIdToFailureLogInfo(controller.GetTraceIdToFailureLogInfo())
{
}

FailureModeViewNode::FailureModeViewNode(FailureModeViewNodeData &&data) : data_(std::move(data)) {}

const FailureModeViewNodeData &FailureModeViewNode::GetData() const
{
    return data_;
}

void FailureModeViewNode::AddSubNode(const FailureModeViewNode &subNode)
{
    subNodes_.push_back(subNode);
}

const std::vector<FailureModeViewNode> &FailureModeViewNode::GetSubNodes() const
{
    return subNodes_;
}

RackResult FailureModeView::Build(
    const std::unordered_set<std::string> &rootFailureModes,
    const std::unordered_map<std::string, FailureModeController> &failureModeIdToController,
    const std::unordered_map<std::string, std::vector<std::shared_ptr<FailureLogInfo>>> &traceIdToFailureLogInfos)
{
    roots_.clear();
    traceIdToFailureLogInfos_ = traceIdToFailureLogInfos;
    roots_.reserve(rootFailureModes.size());
    for (const std::string &rootFailureModeId : rootFailureModes) {
        auto it = failureModeIdToController.find(rootFailureModeId);
        if (it == failureModeIdToController.end()) {
            return RACK_FAIL;
        }
        const FailureModeController &controller = it->second;
        roots_.emplace_back(FailureModeViewNodeData{controller});

        std::unordered_set<std::string> path = {rootFailureModeId};
        RackResult ret = BuildSubTree(roots_.back(), rootFailureModeId, failureModeIdToController, path);
        if (ret != RACK_OK) {
            return ret;
        }
    }
    return RACK_OK;
}

RackResult FailureModeView::Dump(const std::string &outputDir) const
{
    const std::string html = BuildHtml(BuildRootJson(roots_, traceIdToFailureLogInfos_));
    if (html.empty()) {
        return RACK_FAIL;
    }
    RackResult ret = WriteHtml(html, outputDir);
    if (ret != RACK_OK) {
        return ret;
    }
    std::filesystem::path outputPath =
        std::filesystem::path(outputDir.empty() ? DEFAULT_OUTPUT_DIR : outputDir) / HTML_OUTPUT_FILENAME;
    LOG_INFO << "generated visualized failure mode view: " << outputPath;
    return RACK_OK;
}

RackResult FailureModeView::BuildSubTree(
    FailureModeViewNode &parentNode, const std::string &parentFailureModeId,
    const std::unordered_map<std::string, FailureModeController> &failureModeIdToController,
    std::unordered_set<std::string> &path)
{
    auto parentControllerIter = failureModeIdToController.find(parentFailureModeId);
    if (parentControllerIter == failureModeIdToController.end()) {
        return RACK_FAIL;
    }

    std::vector<std::string> subFailureModeIds(parentControllerIter->second.GetSubValidFailureModeIds().begin(),
                                               parentControllerIter->second.GetSubValidFailureModeIds().end());
    std::sort(subFailureModeIds.begin(), subFailureModeIds.end());

    for (const std::string &subFailureModeId : subFailureModeIds) {
        auto childControllerIter = failureModeIdToController.find(subFailureModeId);
        if (childControllerIter == failureModeIdToController.end()) {
            return RACK_FAIL;
        }
        if (path.find(subFailureModeId) != path.end()) {
            continue;
        }

        FailureModeViewNode childNode(FailureModeViewNodeData{childControllerIter->second});
        path.insert(subFailureModeId);
        RackResult ret = BuildSubTree(childNode, subFailureModeId, failureModeIdToController, path);
        path.erase(subFailureModeId);
        if (ret != RACK_OK) {
            return ret;
        }
        parentNode.AddSubNode(childNode);
    }
    return RACK_OK;
}
} // namespace diag
