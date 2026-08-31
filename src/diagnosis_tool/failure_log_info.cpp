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

#include "failure_log_info.h"

#include <stdexcept>
#include <string_view>
#include <utility>

#include "failure_def.h"
#include "failure_log_helper.h"

namespace diag {
namespace {
constexpr char FIELD_SEPARATOR = ':';
constexpr std::pair<std::string_view, LevelOption> LEVEL_MAPPINGS[] = {
    {"I", LevelOption::INFO},  {"W", LevelOption::WARN},  {"D", LevelOption::DEBUG},
    {"E", LevelOption::ERROR}, {"F", LevelOption::FATAL},
};
} // namespace

std::optional<LevelOption> LevelOptionFromString(const std::string &str)
{
    for (const auto &[code, level] : LEVEL_MAPPINGS) {
        if (str == code) {
            return level;
        }
    }
    return std::nullopt;
}

FailureLogInfo::FailureLogInfo(const std::vector<std::string> &fields, const std::string &rawLog) : rawLog(rawLog)
{
    if (fields.size() < RUNTIME_FIELDS_SIZE) {
        throw std::runtime_error("insufficient log fields");
    }
    auto timestampOption = failure::DatetimeStrToTimestamp(log_helper::Trim(fields[TIME_IDX]));
    if (!timestampOption.has_value()) {
        throw std::runtime_error("invalid timestamp: " + fields[TIME_IDX]);
    }
    timestamp = timestampOption.value();
    auto parsedLevel = LevelOptionFromString(log_helper::Trim(fields[LEVEL_IDX]));
    if (!parsedLevel.has_value()) {
        throw std::runtime_error("invalid level: " + fields[LEVEL_IDX]);
    }
    level = parsedLevel.value();
    auto filenameLineNo = log_helper::Trim(fields[FILENAME_LINENO_IDX]);
    auto colonPos = filenameLineNo.rfind(FIELD_SEPARATOR);
    if (colonPos == std::string::npos) {
        throw std::runtime_error("invalid source location: " + filenameLineNo);
    }
    lineNo = std::stoi(filenameLineNo.substr(colonPos + 1));
    const std::string filenameFunction = filenameLineNo.substr(0, colonPos);
    colonPos = filenameFunction.find(FIELD_SEPARATOR);
    if (colonPos == std::string::npos) {
        filename = filenameFunction;
    } else {
        filename = filenameFunction.substr(0, colonPos);
        functionName = filenameFunction.substr(colonPos + 1);
    }
    podName = log_helper::Trim(fields[PODNAME_IDX]);
    auto pidTid = log_helper::Trim(fields[PID_TID_IDX]);
    colonPos = pidTid.find(FIELD_SEPARATOR);
    pid = std::stoi(pidTid.substr(0, colonPos));
    tid = std::stoi(pidTid.substr(colonPos + 1));
    traceId = log_helper::Trim(fields[TRACEID_IDX]);
    clusterName = log_helper::Trim(fields[CLUSTERNAME_IDX]);
}

void FailureLogInfo::BindFailureMode(const std::string &failureModeId)
{
    failureModeIds.push_back(failureModeId);
}

FailureLogInfoAccess::FailureLogInfoAccess(const std::vector<std::string> &fields, const std::string &rawLog)
    : FailureLogInfo(fields, rawLog)
{
    if (fields.size() < ACCESS_FIELDS_SIZE) {
        throw std::runtime_error("insufficient access log fields");
    }
    statusCode = std::stoi(log_helper::Trim(fields[STATUSCODE_IDX]));
    action = log_helper::Trim(fields[ACTION_IDX]);
    cost = std::stoi(log_helper::Trim(fields[COST_IDX]));
    dataSize = std::stoi(log_helper::Trim(fields[DATASIZE_IDX]));
    reqMsg = log_helper::Trim(fields[REQMSG_IDX]);
    respMsg = log_helper::Trim(fields[RESPMSG_IDX]);
}

FailureLogInfoRuntime::FailureLogInfoRuntime(const std::vector<std::string> &fields, const std::string &rawLog)
    : FailureLogInfo(fields, rawLog)
{
    message = log_helper::Trim(fields[MESSAGE_IDX]);
}

} // namespace diag
