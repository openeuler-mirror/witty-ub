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

#define MODULE_NAME "CONTEXT"
#include "ubse_context.h"
#include <algorithm>
#include <filesystem>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <thread>
#include <typeindex>
#include "rack_error.h"
#include "rack_module.h"
#include "logger.h"

namespace ubse::context {
constexpr const char *WITTY_DIR = "/var/witty-ub";
constexpr std::size_t DASH_PREFIX_LEN = 2;
constexpr std::size_t MAX_POD_ID_LEN = 253;

RackResult UbseContext::CreateWittyDir()
{
    if (!std::filesystem::exists(WITTY_DIR)) {
        if (!std::filesystem::create_directory(WITTY_DIR)) {
            LOG_ERROR << "UbseContext::CreateWittyDir-Error: failed to create witty log directory: " << WITTY_DIR;
            return RACK_FAIL;
        }
    }
    return RACK_OK;
}

RackResult UbseContext::ParseArgs(int argc, char *argv[])
{
    int i = 1;
    while (i < argc) {
        std::string arg = argv[i];
        if (arg.substr(0, DASH_PREFIX_LEN) != "--") {
            LOG_ERROR << "UbseContext::ParseArgs-Error: parsing arguments " << arg;
            return RACK_FAIL;
        }
        std::string key = arg.substr(DASH_PREFIX_LEN);
        if (key.empty()) {
            LOG_ERROR << "UbseContext::ParseArgs-Error: parsing arguments " << arg;
            return RACK_FAIL;
        }
        std::string value;
        if (i + 1 < argc && argv[i + 1][0] != '-') {
            value = argv[++i];
        } else {
            LOG_ERROR << "UbseContext::ParseArgs-Error: empty argument " << arg;
            return RACK_FAIL;
        }
        argMap[key] = value;
        i++;
    }
    LOG_INFO << "UbseContext::ParseArgs-Args ";
    for (const auto &it : argMap) {
        LOG_INFO << "[" << it.first << ":" << it.second << "]";
    }
    return RACK_OK;
}
RackResult UbseContext::SortModules()
{
    sortedModules.clear();
    std::queue<std::type_index> moduleQueue;
    for (auto module : initModules) {
        moduleQueue.push(module);
    }
    int cnt = 0;
    while (!moduleQueue.empty()) {
        if (cnt == moduleQueue.size() + 1) {
            LOG_ERROR << "UbseContext::SortModules-Error: circular dependency detected";
            return RACK_FAIL;
        }
        std::type_index currentModule = moduleQueue.front();
        moduleQueue.pop();
        bool flag = true;
        for (auto dep : moduleDeps[currentModule]) {
            if (find(sortedModules.begin(), sortedModules.end(), dep) == sortedModules.end()) {
                flag = false;
                break;
            }
        }
        if (flag) {
            sortedModules.push_back(currentModule);
            cnt = 0;
        } else {
            moduleQueue.push(currentModule);
            cnt += 1;
        }
    }
    return RACK_OK;
}
std::string UbseContext::GetRole()
{
    if (argMap.find("role") == argMap.end()) {
        LOG_ERROR << "UbseContext::GetRole-Error: agr role not defined";
        return "";
    }
    std::string role = argMap["role"];
    LOG_INFO << "UbseContext::GetRole-Info: role is " << role;
    if (role == "analyzer") {
        return role;
    } else if (role == "collector") {
        return role;
    } else {
        LOG_ERROR << "UbseContext::GetRole-Error: role " << role << " not supported";
        return "UNKNOWN";
    }
}
std::vector<std::type_index> UbseContext::GetSortedModules()
{
    SortModules();
    return sortedModules;
}
std::unordered_map<std::type_index, std::shared_ptr<RackModule>> UbseContext::GetModuleMap()
{
    return moduleMap;
}
RackResult UbseContext::InitAndStartModules()
{
    RackResult ret = RACK_OK;
    for (std::type_index moduleType : sortedModules) {
        std::shared_ptr<RackModule> module = moduleMap[moduleType];
        ret = module->Initialize();
        if (ret != RACK_OK) {
            LOG_ERROR << "UbseContext::InitAndStartModules-Error: module " << moduleType.name() << " init failed";
            return ret;
        }
    }
    for (std::type_index moduleType : sortedModules) {
        std::shared_ptr<RackModule> module = moduleMap[moduleType];
        ret = module->Start();
        if (ret != RACK_OK) {
            LOG_ERROR << "UbseContext::InitAndStartModules-Error: module " << moduleType.name() << " start failed";
            return ret;
        }
    }
    return ret;
}
const std::unordered_map<std::string, std::string> &UbseContext::GetArgMap() const
{
    return argMap;
}
RackResult UbseContext::Run(int argc, char *argv[])
{
    RackResult ret = InitAndStartModules();
    if (ret != RACK_OK) {
        LOG_ERROR << "UbseContext::Run-Error: init and start modules failed";
        return ret;
    }
    return ret;
}
std::vector<std::string> split(const std::string &s, char delimiter)
{
    std::vector<std::string> tokens;
    size_t start = 0;
    size_t end = 0;
    while ((end = s.find(delimiter, start)) != std::string::npos) {
        tokens.push_back(s.substr(start, end - start));
        start = end + 1;
    }
    if (start < s.size()) {
        tokens.push_back(s.substr(start));
    }
    return tokens;
}
bool IsValidPodId(const std::string &id)
{
    if (id.empty()) {
        return false;
    }
    if (id.size() > MAX_POD_ID_LEN) {
        return false;
    }

    if (!std::isalnum(static_cast<unsigned char>(id[0]))) {
        return false;
    }
    if (!std::isalnum(static_cast<unsigned char>(id.back()))) {
        return false;
    }
    for (char c : id) {
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-')) {
            return false;
        }
    }
    return true;
}
// Helper function to trim whitespace from both ends of a string
std::string TrimSpace(const std::string &str)
{
    size_t first = str.find_first_not_of(" \t\n\r");
    if (first == std::string::npos) {
        return "";
    }
    size_t last = str.find_last_not_of(" \t\n\r");
    return str.substr(first, last - first + 1);
}

bool IsValidPathEntry(const std::string &entry, std::string &outPodId, std::string &outPath, std::string &outError)
{
    size_t pos = entry.find(':');
    if (pos == std::string::npos) {
        outError = "missing or invalid pod id";
        return false;
    }

    // Extract and trim podId and path parts
    outPodId = TrimSpace(entry.substr(0, pos));
    outPath = TrimSpace(entry.substr(pos + 1));

    if (!IsValidPodId(outPodId)) {
        outError = "invalid pod id characters";
        return false;
    }

    if (outPath.empty() || outPath[0] != '/') {
        outError = "path must be absolute (start with '/')";
        return false;
    }

    return true;
}
namespace {
struct ParsedTopoArgs {
    std::string networkMode;
    std::string podMode;
    std::string umqLogPath;
    std::string podId;
    bool hasNetworkMode = false;
    bool hasPodMode = false;
    bool hasUmqLogPath = false;
    bool hasPodId = false;
    std::map<std::string, std::string> pathMap;
    std::vector<std::string> podIdList;
};

RackResult ParseTopoArgsLoop(int argc, char *argv[], ParsedTopoArgs &parsed)
{
    int i = 1;
    while (i < argc) {
        std::string arg = argv[i];
        if (arg == "--network-mode") {
            if (i + 1 >= argc) {
                LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: missing network mode value";
                return RACK_FAIL;
            }
            parsed.networkMode = argv[++i];
            if (parsed.networkMode != "fullmesh" && parsed.networkMode != "clos") {
                LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: invalid network mode value "
                          << parsed.networkMode;
                return RACK_FAIL;
            }
            LOG_DEBUG << "UbseConetext::ParseTopoToolsArgs-Debug: network mode is " << parsed.networkMode;
            parsed.hasNetworkMode = true;
        } else if (arg == "--pod-mode") {
            if (i + 1 >= argc) {
                LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: missing pod mode value";
                return RACK_FAIL;
            }
            parsed.podMode = argv[++i];
            if (parsed.podMode != "on" && parsed.podMode != "off") {
                LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: invalid pod mode value " << parsed.podMode;
                return RACK_FAIL;
            }
            LOG_DEBUG << "UbseConetext::ParseTopoToolsArgs-Debug: pod mode is " << parsed.podMode;
            parsed.hasPodMode = true;
        } else if (arg == "--umq-log-path") {
            if (i + 1 >= argc) {
                LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: missing umq log path value";
                return RACK_FAIL;
            }
            parsed.umqLogPath = argv[++i];
            LOG_DEBUG << "UbseConetext::ParseTopoToolsArgs-Debug: umq log path is " << parsed.umqLogPath;
            parsed.hasUmqLogPath = true;
        } else if (arg == "--pod-id") {
            if (i + 1 >= argc) {
                LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: missing pod id value";
                return RACK_FAIL;
            }
            parsed.podId = argv[++i];
            LOG_DEBUG << "UbseConetext::ParseTopoToolsArgs-Debug: pod id is " << parsed.podId;
            parsed.hasPodId = true;
        } else {
            LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: parsing topo tools arguments " << arg;
            return RACK_FAIL;
        }
        i++;
    }
    return RACK_OK;
}

RackResult ParsePathEntries(const std::string &umqLogPath, ParsedTopoArgs &parsed)
{
    auto entries = split(umqLogPath, ',');
    if (entries.empty()) {
        LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: umq log path is empty";
        return RACK_FAIL;
    }
    for (const auto &entry : entries) {
        std::string podId, pathPart, error;
        if (!IsValidPathEntry(entry, podId, pathPart, error)) {
            LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: invalid umq log path entry " << entry << " - "
                      << error;
            return RACK_FAIL;
        }
        if (parsed.pathMap.count(podId)) {
            LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: pod id " << podId << " is duplicated in umq log path";
            return RACK_FAIL;
        }
        parsed.pathMap[podId] = pathPart;
    }
    return RACK_OK;
}

RackResult ValidatePodIdList(ParsedTopoArgs &parsed)
{
    parsed.podIdList = split(parsed.podId, ',');
    std::set<std::string> allowed;
    for (const auto &[podId, _] : parsed.pathMap) {
        allowed.insert(podId);
    }
    for (const auto &d : parsed.podIdList) {
        if (d.empty()) {
            LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: empty pod id in pod id list";
            return RACK_FAIL;
        }
        if (allowed.find(d) == allowed.end()) {
            LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: pod id " << d << " not found in umq log path";
            return RACK_FAIL;
        }
    }
    return RACK_OK;
}

RackResult BuildPathMap(ParsedTopoArgs &parsed)
{
    if (parsed.podMode == "on") {
        if (!parsed.hasUmqLogPath) {
            LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: umq log path is required when pod mode is on";
            return RACK_FAIL;
        }
        if (ParsePathEntries(parsed.umqLogPath, parsed) != RACK_OK) {
            return RACK_FAIL;
        }
        if (parsed.hasPodId && ValidatePodIdList(parsed) != RACK_OK) {
            return RACK_FAIL;
        }
    } else {
        if (!parsed.hasUmqLogPath) {
            parsed.umqLogPath = "/var/log/messages";
        }
        parsed.pathMap["normal"] = parsed.umqLogPath;
        LOG_DEBUG << "UbseConetext::ParseTopoToolsArgs-Debug: normal log path is " << parsed.umqLogPath;
    }
    return RACK_OK;
}

RackResult ValidateTopoArgs(ParsedTopoArgs &parsed)
{
    if (!parsed.hasNetworkMode) {
        LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: missing network mode";
        return RACK_FAIL;
    }
    if (!parsed.hasPodMode) {
        LOG_ERROR << "UbseConetext::ParseTopoToolsArgs-Error: missing pod mode";
        return RACK_FAIL;
    }
    return BuildPathMap(parsed);
}
} // namespace

RackResult UbseContext::ParseTopoToolsArgs(int argc, char *argv[])
{
    ParsedTopoArgs parsed;
    if (ParseTopoArgsLoop(argc, argv, parsed) != RACK_OK) {
        return RACK_FAIL;
    }
    if (ValidateTopoArgs(parsed) != RACK_OK) {
        return RACK_FAIL;
    }
    topoArgs.networkMode = parsed.networkMode;
    topoArgs.podMode = parsed.podMode;
    topoArgs.umq_log_path_map = parsed.pathMap;
    topoArgs.pod_id_list = parsed.podIdList;
    LOG_INFO << "UbseConetext::ParseTopoToolsArgs-Info: Validation passed, ready to run ";
    return RACK_OK;
}
} // namespace ubse::context