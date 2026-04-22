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

#include "log_collector.h"
#include "logger.h"
#include <fstream>
#include <sstream>
#include <algorithm>

namespace brpc {

string SystemLog::logPath;
string BrpcLog::logPath;

// 读取文件全部内容，返回文件文本字符串
static string ReadFileContent(const string &path)
{
    ifstream file(path);
    if (!file.is_open()) {
        LOG_ERROR << "failed to open log file: " << path;
        return "";
    }
    ostringstream oss;
    oss << file.rdbuf();
    return oss.str();
}

// 按行拆分文本内容，过滤空行
static vector<string> SplitLines(const string &content)
{
    vector<string> lines;
    istringstream stream(content);
    string line;
    while (getline(stream, line)) {
        if (!line.empty()) {
            lines.push_back(line);
        }
    }
    return lines;
}

// 收集系统日志，读取SystemLog::logPath指向的文件并按行转化为SystemLog结构体
vector<SystemLog> LogCollector::CollectSystemLog(int64_t timestamp)
{
    vector<SystemLog> logs;
    string content = ReadFileContent(SystemLog::logPath);
    if (content.empty()) {
        LOG_WARN << "system log is empty or file not found: " << SystemLog::logPath;
        return logs;
    }

    // 按行拆分日志内容，每行转化为一个SystemLog条目
    auto lines = SplitLines(content);
    for (auto &line : lines) {
        SystemLog logEntry;
        logEntry.text = line;
        logs.push_back(logEntry);
    }

    LOG_INFO << "collected " << logs.size() << " system log entries";
    return logs;
}

// 收集BRPC日志，读取BrpcLog::logPath指向的文件并按行转化为BrpcLog结构体
vector<BrpcLog> LogCollector::CollectBrpcLog(int64_t timestamp)
{
    vector<BrpcLog> logs;
    string content = ReadFileContent(BrpcLog::logPath);
    if (content.empty()) {
        LOG_WARN << "brpc log is empty or file not found: " << BrpcLog::logPath;
        return logs;
    }

    // 按行拆分日志内容，每行转化为一个BrpcLog条目
    auto lines = SplitLines(content);
    for (auto &line : lines) {
        BrpcLog logEntry;
        logEntry.text = line;
        logs.push_back(logEntry);
    }

    LOG_INFO << "collected " << logs.size() << " brpc log entries";
    return logs;
}

}