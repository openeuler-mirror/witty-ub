#define MODULE_NAME "DIAGNOSIS"

#include "failure_mode_view.h"

#include <sys/stat.h>

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <json/json.h>
#include <sstream>
#include <vector>

#include "logger.h"

namespace diag {
namespace {
constexpr const char *DEFAULT_OUTPUT_PATH = "/var/witty-ub/failure-mode-view-vis.html";
constexpr const char *VIEW_VIS_RUNTIME_RESOURCE_DIR = "/usr/share/witty-ub/data/view-vis";
constexpr const char *VIEW_VIS_SOURCE_RESOURCE_DIR = "data/view-vis";
constexpr const char *HTML_TEMPLATE_NAME = "failure_mode_view.html";
constexpr const char *CSS_RESOURCE_NAME = "failure_mode_view.css";
constexpr const char *JS_RESOURCE_NAME = "failure_mode_view.js";
constexpr const char *DATA_PLACEHOLDER = "__FAILURE_MODE_VIEW_DATA__";
constexpr const char *CSS_PLACEHOLDER = "__FAILURE_MODE_VIEW_CSS__";
constexpr const char *JS_PLACEHOLDER = "__FAILURE_MODE_VIEW_JS__";
constexpr mode_t OUTPUT_FILE_PERM_640 = 0640;

FailureModeViewNode MakeViewNode(FailureModeController &controller)
{
    auto failureMode = controller.GetFailureMode();
    const std::string &id = failureMode->GetId();
    const std::string &name = failureMode->GetName();
    const std::string &cause = failureMode->GetRootCauseDesc();
    const std::string &suggestion = failureMode->GetFixSuggDesc();
    const std::string &validation = failureMode->GetValidationMethodDesc();
    int hitCount = controller.GetHitCount();
    return FailureModeViewNode(id, name, cause, suggestion, validation, hitCount);
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

Json::Value NodeToJson(const FailureModeViewNode &node)
{
    Json::Value nodeJson(Json::objectValue);
    nodeJson["id"] = node.GetId();
    nodeJson["name"] = node.GetName();
    nodeJson["cause"] = node.GetCause();
    nodeJson["suggestion"] = node.GetSuggestion();
    nodeJson["validation"] = node.GetValidation();
    nodeJson["hit_count"] = node.GetHitCount();
    nodeJson["children"] = Json::Value(Json::arrayValue);

    std::vector<const FailureModeViewNode *> children;
    children.reserve(node.GetSubFailureModeNodes().size());
    for (const FailureModeViewNode &child : node.GetSubFailureModeNodes()) {
        children.push_back(&child);
    }
    std::sort(children.begin(), children.end(), [](const FailureModeViewNode *left, const FailureModeViewNode *right) {
        if (left->GetId() != right->GetId()) {
            return left->GetId() < right->GetId();
        }
        return left->GetName() < right->GetName();
    });
    for (const FailureModeViewNode *child : children) {
        nodeJson["children"].append(NodeToJson(*child));
    }
    return nodeJson;
}

Json::Value BuildRootJson(const std::vector<FailureModeViewNode> &roots)
{
    Json::Value root(Json::objectValue);
    root["trees"] = Json::Value(Json::arrayValue);

    std::vector<const FailureModeViewNode *> sortedRoots;
    sortedRoots.reserve(roots.size());
    for (const FailureModeViewNode &node : roots) {
        sortedRoots.push_back(&node);
    }
    std::sort(sortedRoots.begin(), sortedRoots.end(), [](const FailureModeViewNode *left, const FailureModeViewNode *right) {
        if (left->GetId() != right->GetId()) {
            return left->GetId() < right->GetId();
        }
        return left->GetName() < right->GetName();
    });
    for (const FailureModeViewNode *node : sortedRoots) {
        root["trees"].append(NodeToJson(*node));
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

FailureModeViewNode::FailureModeViewNode(const std::string &id, const std::string &name, const std::string &cause,
                                         const std::string &suggestion, const std::string &validation, int hitCount)
    : id_(id),
      name_(name),
      cause_(cause),
      suggestion_(suggestion),
      validation_(validation),
      hitCount_(hitCount)
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

const std::vector<FailureModeViewNode> &FailureModeViewNode::GetSubFailureModeNodes() const
{
    return subFailureModeNodes_;
}

RackResult FailureModeView::Build(const std::unordered_set<std::string> &rootFailureModes,
                                  std::unordered_map<std::string, FailureModeController> &failureModeIdToController)
{
    roots.clear();
    roots.reserve(rootFailureModes.size());
    for (const std::string &rootFailureModeId : rootFailureModes) {
        auto controllerIter = failureModeIdToController.find(rootFailureModeId);
        if (controllerIter == failureModeIdToController.end()) {
            return RACK_FAIL;
        }
        FailureModeController &controller = controllerIter->second;
        if (controller.GetSubFailureModesInView().empty()) {
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
    std::unordered_map<std::string, FailureModeController> &failureModeIdToController, std::unordered_set<std::string> &path)
{
    auto parentControllerIter = failureModeIdToController.find(parentFailureModeId);
    if (parentControllerIter == failureModeIdToController.end()) {
        return RACK_FAIL;
    }

    std::vector<std::string> subFailureModeIds(parentControllerIter->second.GetSubFailureModesInView().begin(),
                                               parentControllerIter->second.GetSubFailureModesInView().end());
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
    const std::string html = BuildHtml(BuildRootJson(roots));
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
