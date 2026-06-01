#define MODULE_NAME "DIAGNOSIS"

#include "failure_mode_view.h"

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
namespace {
constexpr const char *DEFAULT_OUTPUT_PATH = "/var/witty-ub/failure-mode-view-vis.html";
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
using TraceView = std::pair<std::string, const std::vector<FailureLogInfo> *>;

FailureModeViewNode MakeViewNode(FailureModeController &controller)
{
    auto failureMode = controller.GetFailureMode();
    FailureModeViewNodeData data{
        failureMode->GetId(),
        failureMode->GetName(),
        failureMode->GetRootCauseDesc(),
        failureMode->GetFixSuggDesc(),
        failureMode->GetValidationMethodDesc(),
        controller.GetHitCount(),
        controller.GetLogInfos(),
    };
    return FailureModeViewNode(std::move(data));
}

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

Json::Value LogInfoToJson(const FailureLogInfo &logInfo)
{
    Json::Value logJson(Json::objectValue);
    logJson["time"] = FormatLogTime(logInfo.timestamp);
    logJson["timestamp"] = Json::Int64(logInfo.timestamp);
    logJson["failure_mode_id"] = logInfo.failureModeId;
    logJson["filename"] = logInfo.filename;
    logJson["line_no"] = logInfo.lineNo;
    logJson["pod_name"] = logInfo.podName;
    logJson["pid"] = logInfo.pid;
    logJson["tid"] = logInfo.tid;
    logJson["trace_id"] = logInfo.traceId;
    logJson["cluster_name"] = logInfo.clusterName;
    logJson["message"] = logInfo.message;
    return logJson;
}

Json::Value TraceToJson(const std::string &traceId, const std::vector<FailureLogInfo> &trace)
{
    Json::Value traceJson(Json::objectValue);
    traceJson["trace_id"] = traceId;
    traceJson["logs"] = Json::Value(Json::arrayValue);

    std::vector<const FailureLogInfo *> logInfos;
    logInfos.reserve(trace.size());
    for (const FailureLogInfo &logInfo : trace) {
        logInfos.push_back(&logInfo);
    }
    std::sort(logInfos.begin(), logInfos.end(), [](const FailureLogInfo *left, const FailureLogInfo *right) {
        return left->timestamp > right->timestamp;
    });

    if (!logInfos.empty()) {
        int64_t startTime = logInfos.front()->timestamp;
        int64_t endTime = logInfos.front()->timestamp;
        for (const FailureLogInfo *logInfo : logInfos) {
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

    for (const FailureLogInfo *logInfo : logInfos) {
        traceJson["logs"].append(LogInfoToJson(*logInfo));
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
    if (left->GetId() != right->GetId()) {
        return left->GetId() < right->GetId();
    }
    return left->GetName() < right->GetName();
}

int64_t GetLatestTraceTimestamp(const std::vector<FailureLogInfo> &trace)
{
    int64_t latest = 0;
    for (const FailureLogInfo &logInfo : trace) {
        latest = std::max(latest, logInfo.timestamp);
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
    nodeJson["id"] = node.GetId();
    nodeJson["name"] = node.GetName();
    nodeJson["cause"] = node.GetCause();
    nodeJson["suggestion"] = node.GetSuggestion();
    nodeJson["validation"] = node.GetValidation();
    nodeJson["hit_count"] = node.GetHitCount();
    nodeJson["log_infos"] = Json::Value(Json::arrayValue);
    nodeJson["children"] = Json::Value(Json::arrayValue);

    std::vector<const FailureLogInfo *> logInfos;
    logInfos.reserve(node.GetLogInfos().size());
    for (const FailureLogInfo &logInfo : node.GetLogInfos()) {
        logInfos.push_back(&logInfo);
    }
    std::sort(logInfos.begin(), logInfos.end(), [](const FailureLogInfo *left, const FailureLogInfo *right) {
        return left->timestamp > right->timestamp;
    });
    for (const FailureLogInfo *logInfo : logInfos) {
        nodeJson["log_infos"].append(LogInfoToJson(*logInfo));
    }

    std::vector<const FailureModeViewNode *> children;
    children.reserve(node.GetSubFailureModeNodes().size());
    for (const FailureModeViewNode &child : node.GetSubFailureModeNodes()) {
        children.push_back(&child);
    }
    std::sort(children.begin(), children.end(), CompareFailureModeViewNode);
    for (const FailureModeViewNode *child : children) {
        nodeJson["children"].append(NodeToJson(*child));
    }
    return nodeJson;
}

Json::Value BuildRootJson(const std::vector<FailureModeViewNode> &roots,
                          const std::unordered_map<std::string, std::vector<FailureLogInfo>> &traces)
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
    sortedTraces.reserve(traces.size());
    for (const auto &[traceId, trace] : traces) {
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

RackResult WriteHtml(const std::string &html)
{
    const std::filesystem::path outputPath = DEFAULT_OUTPUT_PATH;
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
    if (::chmod(DEFAULT_OUTPUT_PATH, OUTPUT_FILE_PERM_640) != 0) {
        LOG_ERROR << "failed to set file mode 0640 for failure mode view html: " << DEFAULT_OUTPUT_PATH;
        return RACK_FAIL;
    }
    return RACK_OK;
}
} // namespace

FailureModeViewNode::FailureModeViewNode(FailureModeViewNodeData data)
    : id_(std::move(data.id)),
      name_(std::move(data.name)),
      cause_(std::move(data.cause)),
      suggestion_(std::move(data.suggestion)),
      validation_(std::move(data.validation)),
      hitCount_(data.hitCount),
      logInfos_(std::move(data.logInfos))
{
}

FailureModeViewNode &FailureModeViewNode::AddSubFailureModeNode(FailureModeViewNode subFailureModeNode)
{
    subFailureModeNodes_.emplace_back(std::move(subFailureModeNode));
    return subFailureModeNodes_.back();
}

const std::string &FailureModeViewNode::GetId() const
{
    return id_;
}

const std::string &FailureModeViewNode::GetName() const
{
    return name_;
}

const std::string &FailureModeViewNode::GetCause() const
{
    return cause_;
}

const std::string &FailureModeViewNode::GetSuggestion() const
{
    return suggestion_;
}

const std::string &FailureModeViewNode::GetValidation() const
{
    return validation_;
}

int FailureModeViewNode::GetHitCount() const
{
    return hitCount_;
}

const std::vector<FailureLogInfo> &FailureModeViewNode::GetLogInfos() const
{
    return logInfos_;
}

const std::vector<FailureModeViewNode> &FailureModeViewNode::GetSubFailureModeNodes() const
{
    return subFailureModeNodes_;
}

RackResult FailureModeView::Build(const std::unordered_set<std::string> &rootFailureModes,
                                  std::unordered_map<std::string, FailureModeController> &failureModeIdToController,
                                  const std::unordered_map<std::string, std::vector<FailureLogInfo>> &traces)
{
    roots.clear();
    traces_ = traces;
    roots.reserve(rootFailureModes.size());
    for (const std::string &rootFailureModeId : rootFailureModes) {
        auto controllerIter = failureModeIdToController.find(rootFailureModeId);
        if (controllerIter == failureModeIdToController.end()) {
            return RACK_FAIL;
        }
        FailureModeController &controller = controllerIter->second;
        if (controller.GetSubFailureModesValid().empty()) {
            continue;
        }
        roots.emplace_back(MakeViewNode(controller));

        std::unordered_set<std::string> path = {rootFailureModeId};
        RackResult ret = BuildSubTree(roots.back(), rootFailureModeId, failureModeIdToController, path);
        if (ret != RACK_OK) {
            return ret;
        }
    }
    return RACK_OK;
}

RackResult FailureModeView::BuildSubTree(
    FailureModeViewNode &parentNode, const std::string &parentFailureModeId,
    std::unordered_map<std::string, FailureModeController> &failureModeIdToController,
    std::unordered_set<std::string> &path)
{
    auto parentControllerIter = failureModeIdToController.find(parentFailureModeId);
    if (parentControllerIter == failureModeIdToController.end()) {
        return RACK_FAIL;
    }

    std::vector<std::string> subFailureModeIds(parentControllerIter->second.GetSubFailureModesValid().begin(),
                                               parentControllerIter->second.GetSubFailureModesValid().end());
    std::sort(subFailureModeIds.begin(), subFailureModeIds.end());

    for (const std::string &subFailureModeId : subFailureModeIds) {
        auto childControllerIter = failureModeIdToController.find(subFailureModeId);
        if (childControllerIter == failureModeIdToController.end()) {
            return RACK_FAIL;
        }
        if (path.find(subFailureModeId) != path.end()) {
            continue;
        }

        FailureModeViewNode &childNode = parentNode.AddSubFailureModeNode(MakeViewNode(childControllerIter->second));
        path.insert(subFailureModeId);
        RackResult ret = BuildSubTree(childNode, subFailureModeId, failureModeIdToController, path);
        path.erase(subFailureModeId);
        if (ret != RACK_OK) {
            return ret;
        }
    }
    return RACK_OK;
}

RackResult FailureModeView::Dump() const
{
    const std::string html = BuildHtml(BuildRootJson(roots, traces_));
    if (html.empty()) {
        return RACK_FAIL;
    }
    RackResult ret = WriteHtml(html);
    if (ret != RACK_OK) {
        return ret;
    }
    LOG_INFO << "generated visualized failure mode view: " << DEFAULT_OUTPUT_PATH;
    return RACK_OK;
}
} // namespace diag
