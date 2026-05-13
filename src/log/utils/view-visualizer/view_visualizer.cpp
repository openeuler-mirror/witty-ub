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

#define MODULE_NAME "VIEW_VISUALIZER"

#include "view_visualizer.h"

#include <filesystem>
#include <fstream>
#include <sstream>
#include <vector>

#include "logger.h"

namespace view_visualizer {
namespace {
constexpr const char *DEFAULT_INPUT_PATH = "/var/witty-ub/failure-view.json";
constexpr const char *DEFAULT_OUTPUT_PATH = "/var/witty-ub/failure-view-vis.html";
constexpr const char *VIEW_VIS_RUNTIME_RESOURCE_DIR = "/usr/share/witty-ub/data/view-vis";
constexpr const char *VIEW_VIS_SOURCE_RESOURCE_DIR = "data/view-vis";
constexpr const char *HTML_TEMPLATE_NAME = "failure_view.html";
constexpr const char *CSS_RESOURCE_NAME = "failure_view.css";
constexpr const char *JS_RESOURCE_NAME = "failure_view.js";
constexpr const char *DATA_PLACEHOLDER = "__FAILURE_VIEW_DATA__";
constexpr const char *CSS_PLACEHOLDER = "__FAILURE_VIEW_CSS__";
constexpr const char *JS_PLACEHOLDER = "__FAILURE_VIEW_JS__";

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

bool ReplaceFirst(std::string &content, const std::string &placeholder, const std::string &replacement)
{
    const size_t pos = content.find(placeholder);
    if (pos == std::string::npos) {
        return false;
    }
    content.replace(pos, placeholder.size(), replacement);
    return true;
}

} // namespace

RackResult ViewVisualizer::Initialize()
{
    return RACK_OK;
}

void ViewVisualizer::UnInitialize() {}

RackResult ViewVisualizer::Start()
{
    Json::Value root;
    RackResult ret = LoadView(root);
    if (ret != RACK_OK) {
        return ret;
    }
    const std::string html = BuildHtml(root);
    if (html.empty()) {
        return RACK_FAIL;
    }
    ret = WriteHtml(html);
    if (ret != RACK_OK) {
        return ret;
    }
    LOG_INFO << "generated visualized failure view: " << DEFAULT_OUTPUT_PATH;
    return RACK_OK;
}

void ViewVisualizer::Stop() {}

RackResult ViewVisualizer::LoadView(Json::Value &root) const
{
    std::ifstream ifs(DEFAULT_INPUT_PATH);
    if (!ifs.is_open()) {
        LOG_ERROR << "failed to open failure view json: " << DEFAULT_INPUT_PATH;
        return RACK_FAIL;
    }

    Json::CharReaderBuilder builder;
    builder["collectComments"] = false;
    std::string errors;
    if (!Json::parseFromStream(builder, ifs, &root, &errors)) {
        LOG_ERROR << "failed to parse failure view json: " << DEFAULT_INPUT_PATH << ", error: " << errors;
        return RACK_FAIL;
    }
    if (!root.isObject() || !root["callstack_views"].isArray()) {
        LOG_ERROR << "invalid failure view json: missing array callstack_views";
        return RACK_FAIL;
    }
    return RACK_OK;
}

RackResult ViewVisualizer::WriteHtml(const std::string &html) const
{
    const std::filesystem::path outputPath = DEFAULT_OUTPUT_PATH;
    std::error_code ec;
    const std::filesystem::path parent = outputPath.parent_path();
    if (!parent.empty()) {
        std::filesystem::create_directories(parent, ec);
        if (ec) {
            LOG_ERROR << "failed to create output directory: " << parent << ", error: " << ec.message();
            return RACK_FAIL;
        }
    }

    std::ofstream ofs(outputPath, std::ios::out | std::ios::trunc);
    if (!ofs.is_open()) {
        LOG_ERROR << "failed to open output html: " << outputPath;
        return RACK_FAIL;
    }
    ofs << html;
    ofs.flush();
    if (!ofs.good()) {
        LOG_ERROR << "failed to write output html: " << outputPath;
        return RACK_FAIL;
    }
    return RACK_OK;
}

RackResult ViewVisualizer::ReadResourceFile(const std::string &fileName, std::string &content) const
{
    std::filesystem::path sourceResourcePath = VIEW_VIS_SOURCE_RESOURCE_DIR;
    sourceResourcePath.append(fileName);
    std::filesystem::path relativeResourcePath = std::filesystem::path(__FILE__).parent_path();
    relativeResourcePath.append("../../../../data/view-vis");
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

    LOG_ERROR << "failed to read view visualizer resource: " << fileName;
    return RACK_FAIL;
}

std::string ViewVisualizer::BuildHtml(const Json::Value &root) const
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
        LOG_ERROR << "view visualizer template missing data placeholder: " << DATA_PLACEHOLDER;
        return "";
    }
    if (!ReplaceFirst(htmlTemplate, CSS_PLACEHOLDER, css)) {
        LOG_ERROR << "view visualizer template missing css placeholder: " << CSS_PLACEHOLDER;
        return "";
    }
    if (!ReplaceFirst(htmlTemplate, JS_PLACEHOLDER, js)) {
        LOG_ERROR << "view visualizer template missing js placeholder: " << JS_PLACEHOLDER;
        return "";
    }

    return htmlTemplate;
}
} // namespace view_visualizer
