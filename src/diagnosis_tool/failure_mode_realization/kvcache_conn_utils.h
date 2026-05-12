#pragma once

#include <cstdio>
#include <memory>
#include <string>
#include <array>
#include <sstream>

namespace diag {
namespace kvcache_conn_utils {

inline std::string RunCommand(const std::string &cmd)
{
    std::array<char, 128> buffer;
    std::string result;
    std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd.c_str(), "r"), pclose);
    if (!pipe) {
        return "";
    }
    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    return result;
}

inline bool GrepOutputNonEmpty(const std::string &grepCmd)
{
    std::string output = RunCommand(grepCmd);
    return !output.empty();
}

inline bool HasCodeInUniqOutput(const std::string &uniqOutput, const std::vector<int> &codes)
{
    // uniq -c 输出格式: "<count> <code>"
    std::istringstream stream(uniqOutput);
    std::string line;
    while (std::getline(stream, line)) {
        std::istringstream lineStream(line);
        int count, code;
        if (lineStream >> count >> code) {
            for (int target : codes) {
                if (code == target) {
                    return true;
                }
            }
        }
    }
    return false;
}

inline bool HasNonZeroCode(const std::string &uniqOutput)
{
    std::istringstream stream(uniqOutput);
    std::string line;
    while (std::getline(stream, line)) {
        std::istringstream lineStream(line);
        int count, code;
        if (lineStream >> count >> code) {
            if (code != 0) {
                return true;
            }
        }
    }
    return false;
}

inline bool HasCodeZeroWithNotFound(const std::string &accessLogOutput)
{
    // access log 格式: "code | handleName | ... | respMsg"
    // 查找 code=0 且 respMsg 含 NOT_FOUND 或 Can't find object
    std::istringstream stream(accessLogOutput);
    std::string line;
    while (std::getline(stream, line)) {
        size_t firstPipe = line.find('|');
        if (firstPipe == std::string::npos) continue;
        std::string codeStr = line.substr(0, firstPipe);
        // 去除空格
        codeStr.erase(0, codeStr.find_first_not_of(" \t"));
        codeStr.erase(codeStr.find_last_not_of(" \t") + 1);
        if (codeStr == "0") {
            size_t lastPipe = line.rfind('|');
            if (lastPipe != std::string::npos) {
                std::string respMsg = line.substr(lastPipe + 1);
                if (respMsg.find("NOT_FOUND") != std::string::npos ||
                    respMsg.find("Can't find object") != std::string::npos) {
                    return true;
                }
            }
        }
    }
    return false;
}

inline bool HasMetricsIncreased(const std::string &metricsOutput, const std::string &metricName)
{
    // Metrics Summary 格式: "<metric>=+<N>"
    std::istringstream stream(metricsOutput);
    std::string line;
    while (std::getline(stream, line)) {
        if (line.find(metricName) != std::string::npos) {
            // 提取 +N 部分
            size_t eqPos = line.find('=');
            if (eqPos != std::string::npos) {
                std::string valStr = line.substr(eqPos + 1);
                if (!valStr.empty() && valStr[0] == '+') {
                    int val = std::stoi(valStr.substr(1));
                    if (val > 0) return true;
                }
            }
        }
    }
    return false;
}

inline bool ProcessExists(const std::string &processName)
{
    std::string cmd = "pgrep -af " + processName + " 2>/dev/null";
    std::string output = RunCommand(cmd);
    return !output.empty();
}

inline bool PortListening(const std::string &port)
{
    std::string cmd = "ss -tnlp | grep " + port + " 2>/dev/null";
    std::string output = RunCommand(cmd);
    return !output.empty();
}

} // namespace kvcache_conn_utils
} // namespace diag
