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

#define MODULE_NAME "URMA"
#include <sys/stat.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <regex>
#include <string>
#include <vector>

#include "logger.h"
#include "ubse_context.h"
#include "urma_data_def.h"
#include "urma_topology.h"
namespace urma::topo {
using namespace ubse::context;
constexpr std::size_t LOCAL_EID_GROUP = 1;
constexpr std::size_t LOCAL_JETTY_ID_GROUP = 2;
constexpr std::size_t REMOTE_EID_GROUP = 3;
constexpr std::size_t REMOTE_JETTY_ID_GROUP = 4;
constexpr std::size_t EXPECTED_MATCH_COUNT = 5;
// 解析函数：提取local eid, local jetty_id, remote eid, remote jetty_id
bool ParseLogLine(const std::string &line, SessionKey &key)
{
    std::string pattern = std::string(R"(local eid:\s*([0-9a-fA-F:]+),\s*local jetty_id:\s*(\d+),)") +
                          R"(\s*remote eid:\s*([0-9a-fA-F:]+),\s*remote jetty_id:\s*(\d+))";
    std::regex re(pattern);
    std::smatch m;
    if (std::regex_search(line, m, re)) {
        if (m.size() == EXPECTED_MATCH_COUNT) {
            key.localEid = m[LOCAL_EID_GROUP].str();
            key.localJettyId = m[LOCAL_JETTY_ID_GROUP].str();
            key.remoteEid = m[REMOTE_EID_GROUP].str();
            key.remoteJettyId = m[REMOTE_JETTY_ID_GROUP].str();
            return true;
        }
    }
    return false;
}

std::vector<std::string> URMATopology::CollectLogFiles(const std::string &filePath)
{
    std::vector<std::string> log_files;
    if (std::filesystem::is_directory(filePath)) {
        LOG_DEBUG << "Path is directory, collecting all .log files from: " << filePath;
        for (const auto &entry : std::filesystem::directory_iterator(filePath)) {
            if (entry.path().extension() == ".log") {
                log_files.push_back(entry.path().string());
                LOG_DEBUG << "Found log file: " << entry.path().string();
            }
        }
        if (log_files.empty()) {
            LOG_WARN << "No .log files found in directory: " << filePath;
        }
    } else if (std::filesystem::is_regular_file(filePath)) {
        log_files.push_back(filePath);
    }
    return log_files;
}

URMAResult URMATopology::ProcessLogFile(const std::string &logFile, std::map<SessionKey, std::string> &activeSessions)
{
    LOG_DEBUG << "Processing log file: " << logFile;
    std::ifstream file(logFile);
    if (!file.is_open()) {
        LOG_ERROR << "open file: " << logFile << " fails";
        return URMA_FAIL;
    }
    std::string line;
    int lineNum = 0;
    while (std::getline(file, line)) {
        lineNum++;
        if (line.empty()) {
            continue;
        }
        LOG_DEBUG << "line is: " << line;
        bool isBind = (line.find("bind jetty success") != std::string::npos);
        bool isUnbind = (line.find("unbind jetty") != std::string::npos);
        if (!isBind && !isUnbind) {
            LOG_DEBUG << "line does not contain bind jetty success or unbind jetty";
            continue;
        }
        SessionKey key;
        if (!ParseLogLine(line, key)) {
            LOG_DEBUG << "line: " << lineNum << " log format is incorrect,"
                      << " key: " << (isBind ? "bind network success" : "unbind network") << " is found,"
                      << "but cannot get [local eid, local jetty_id, remote eid, remote jetty_id]";
            LOG_ERROR << "This log line: " << line << " cannot be analyzed, data cannot be correctly matched.";
            file.close();
            return URMA_FAIL;
        }
        if (isBind) {
            activeSessions[key] = line;
            LOG_DEBUG << "line: " << lineNum << " is bind jetty success -> insert/update data: " << key.ToString();
        } else if (isUnbind) {
            activeSessions.erase(key);
            LOG_DEBUG << "line: " << lineNum << " is unbind jetty -> delete bind data: " << key.ToString();
        }
    }
    file.close();
    return URMA_SUCCESS;
}

URMAResult URMATopology::ParseUMQLog(std::string filePath, std::map<SessionKey, std::string> &activeSessions)
{
    LOG_DEBUG << "Start open umq log file.";
    if (!std::filesystem::exists(filePath)) {
        LOG_ERROR << "file: " << filePath << " is not exists";
        return URMA_FAIL;
    }
    std::vector<std::string> log_files = CollectLogFiles(filePath);
    if (log_files.empty()) {
        return URMA_SUCCESS;
    }
    for (const auto &log_file : log_files) {
        if (ProcessLogFile(log_file, activeSessions) != URMA_SUCCESS) {
            return URMA_FAIL;
        }
    }
    return URMA_SUCCESS;
}

URMAResult URMATopology::CreatePodModeTopology(const TopoToolsArgs &args, std::vector<topology::urma::Pod> &pods,
                                               std::vector<topology::urma::Jetty> &jetties,
                                               std::vector<topology::urma::URMADevice> &urma_devices)
{
    auto input_umq_log_path = args.umq_log_path_map;
    std::map<std::string, std::string> target_log_path;
    // 对 pod_id和umq_log_path列出的pod进行一个匹配
    if (args.pod_id_list.empty()) {
        target_log_path = input_umq_log_path;
    } else {
        for (auto pod_id : args.pod_id_list) {
            auto it = input_umq_log_path.find(pod_id);
            if (it == input_umq_log_path.end()) {
                LOG_ERROR << "Failed to find pod " << pod_id << "in input umq_log_path";
                return URMA_FAIL;
            }
            target_log_path.emplace(it->first, it->second);
        }
    }
    for (auto [pod_id, path] : target_log_path) {
        // 获取这个pod对应的日志文件中的所有符合格式日志的参数存在sessionKey中
        std::map<SessionKey, std::string> activeSessions;
        URMAResult ret = ParseUMQLog(path, activeSessions);
        if (ret != URMA_SUCCESS) {
            LOG_ERROR << "error when parsing UMQ log, pod_id is: " << pod_id << " log path is: " << path;
            return ret;
        }
        pods.emplace_back(pod_id);
        for (const auto pair : activeSessions) {
            auto key = pair.first;
            jetties.emplace_back(key.localJettyId, key.localEid, key.remoteJettyId, key.remoteEid, pod_id);
            urma_devices.emplace_back(key.localEid);
        }
    }
    auto pod_pair = jsonModule->GetJsonPair("pod", pods);
    auto jetty_pair = jsonModule->GetJsonPair("jetty", jetties);
    auto urma_device_pair = jsonModule->GetJsonPair("urma_device", urma_devices);
    auto ret = jsonModule->WriteVectorsToFile(URMA_JSON_PATH, pod_pair, jetty_pair, urma_device_pair);
    if (ret == RACK_FAIL) {
        LOG_ERROR << "Failed to writer to file " << URMA_JSON_PATH;
        return URMA_SUCCESS;
    }
    if (::chmod(URMA_JSON_PATH, URMA_JSON_PATH_PERM_640) != 0) {
        LOG_ERROR << "Failed to set file mode 0640 for output file " << URMA_JSON_PATH;
    }
    return URMA_SUCCESS;
}

URMAResult URMATopology::CreateNormalModeTopology(const std::map<std::string, std::string> &input_umq_log_path,
                                                  std::vector<topology::urma::Jetty> &jetties,
                                                  std::vector<topology::urma::URMADevice> &urma_devices)
{
    auto it = input_umq_log_path.find("normal");
    if (it == input_umq_log_path.end()) {
        LOG_ERROR << "Failed to find umq log path when pod mode is off";
        return URMA_FAIL;
    }
    std::map<SessionKey, std::string> activeSessions;
    URMAResult ret = ParseUMQLog(it->second, activeSessions);
    if (ret != URMA_SUCCESS) {
        LOG_ERROR << "error when parsing UMQ log, path is: " << it->second;
        return ret;
    }
    for (const auto pair : activeSessions) {
        auto key = pair.first;
        jetties.emplace_back(key.localJettyId, key.localEid, key.remoteJettyId, key.remoteEid, std::nullopt);
        urma_devices.emplace_back(key.localEid);
    }
    auto jetty_pair = jsonModule->GetJsonPair("jetty", jetties);
    auto urma_device_pair = jsonModule->GetJsonPair("urma_device", urma_devices);
    auto json_ret = jsonModule->WriteVectorsToFile(URMA_JSON_PATH, jetty_pair, urma_device_pair);
    if (json_ret == RACK_FAIL) {
        LOG_ERROR << "Failed to writer to file " << URMA_JSON_PATH;
        return URMA_FAIL;
    }
    if (::chmod(URMA_JSON_PATH, URMA_JSON_PATH_PERM_640) != 0) {
        LOG_ERROR << "Failed to set file mode 0640 for output file " << URMA_JSON_PATH;
    }
    return URMA_SUCCESS;
}

URMAResult URMATopology::CreateTopology(TopoToolsArgs &args)
{
    std::vector<topology::urma::Pod> pods;
    std::vector<topology::urma::Jetty> jetties;
    std::vector<topology::urma::URMADevice> urma_devices;
    if (args.podMode == "on") {
        return CreatePodModeTopology(args, pods, jetties, urma_devices);
    }
    if (args.podMode == "off") {
        return CreateNormalModeTopology(args.umq_log_path_map, jetties, urma_devices);
    }
    LOG_ERROR << "Unknown pod mode: " << args.podMode;
    return URMA_FAIL;
}

} // namespace urma::topo