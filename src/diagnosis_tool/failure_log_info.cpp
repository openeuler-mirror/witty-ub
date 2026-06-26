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

#include "failure_def.h"
#include "failure_log_helper.h"

namespace diag {
std::optional<LevelOption> LevelOptionFromString(const std::string &str)
{
    if (str == "I") {
        return LevelOption::INFO;
    }
    if (str == "W") {
        return LevelOption::WARN;
    }
    if (str == "D") {
        return LevelOption::DEBUG;
    }
    if (str == "E") {
        return LevelOption::ERROR;
    }
    return std::nullopt;
}

FailureLogInfo::FailureLogInfo(const std::vector<std::string> &fields, const std::string &rawLog) : rawLog(rawLog)
{
    auto timestampOption = failure::DatetimeStrToTimestamp(log_helper::Trim(fields[TIME_IDX]));
    if (!timestampOption.has_value()) {
        throw std::runtime_error("invalid timestamp: " + fields[TIME_IDX]);
    }
    timestamp = timestampOption.value();
    auto level = LevelOptionFromString(log_helper::Trim(fields[LEVEL_IDX]));
    if (!level.has_value()) {
        throw std::runtime_error("invalid level: " + fields[LEVEL_IDX]);
    }
    level = level.value();
    auto filenameLineNo = log_helper::Trim(fields[FILENAME_LINENO_IDX]);
    auto colonPos = filenameLineNo.find(':');
    filename = filenameLineNo.substr(0, colonPos);
    lineNo = std::stoi(filenameLineNo.substr(colonPos + 1));
    podName = log_helper::Trim(fields[PODNAME_IDX]);
    auto pidTid = log_helper::Trim(fields[PID_TID_IDX]);
    colonPos = pidTid.find(':');
    pid = std::stoi(pidTid.substr(0, colonPos));
    tid = std::stoi(pidTid.substr(colonPos + 1));
    traceId = log_helper::Trim(fields[TRACEID_IDX]);
    clusterName = log_helper::Trim(fields[CLUSTERNAME_IDX]);
}

bool FailureLogInfo::operator==(const FailureLogInfo &other) const
{
    return timestamp == other.timestamp && level == other.level && filename == other.filename &&
           lineNo == other.lineNo && podName == other.podName && pid == other.pid && tid == other.tid &&
           traceId == other.traceId && clusterName == other.clusterName;
}

void FailureLogInfo::BindFailureMode(const std::string &failureModeId)
{
    failureModeIds.push_back(failureModeId);
}

FailureLogInfoAccess::FailureLogInfoAccess(const std::vector<std::string> &fields, const std::string &rawLog)
    : FailureLogInfo(fields, rawLog)
{
    statusCode = std::stoi(log_helper::Trim(fields[STATUSCODE_IDX]));
    action = log_helper::Trim(fields[ACTION_IDX]);
    cost = std::stoi(log_helper::Trim(fields[COST_IDX]));
    dataSize = std::stoi(log_helper::Trim(fields[DATASIZE_IDX]));
    reqMsg = log_helper::Trim(fields[REQMSG_IDX]);
    respMsg = log_helper::Trim(fields[RESPMSG_IDX]);
}

bool FailureLogInfoAccess::operator==(const FailureLogInfoAccess &other) const
{
    return FailureLogInfo::operator==(other) && statusCode == other.statusCode && action == other.action &&
           cost == other.cost && dataSize == other.dataSize && reqMsg == other.reqMsg && respMsg == other.respMsg;
}

FailureLogInfoRuntime::FailureLogInfoRuntime(const std::vector<std::string> &fields, const std::string &rawLog)
    : FailureLogInfo(fields, rawLog)
{
    message = log_helper::Trim(fields[MESSAGE_IDX]);
}

bool FailureLogInfoRuntime::operator==(const FailureLogInfoRuntime &other) const
{
    return FailureLogInfo::operator==(other) && message == other.message;
}

} // namespace diag