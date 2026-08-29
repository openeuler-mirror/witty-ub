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

#ifndef FAILURE_LOG_INFO_H
#define FAILURE_LOG_INFO_H

#include <cstddef>
#include <optional>
#include <string>
#include <vector>

namespace diag {
// 公共字段
inline constexpr std::size_t TIME_IDX = 0;
inline constexpr std::size_t LEVEL_IDX = 1;
inline constexpr std::size_t FILENAME_LINENO_IDX = 2;
inline constexpr std::size_t PODNAME_IDX = 3;
inline constexpr std::size_t PID_TID_IDX = 4;
inline constexpr std::size_t TRACEID_IDX = 5;
inline constexpr std::size_t CLUSTERNAME_IDX = 6;

// 接口日志字段
inline constexpr std::size_t ACCESS_FIELDS_SIZE = 13;
inline constexpr std::size_t STATUSCODE_IDX = 7;
inline constexpr std::size_t ACTION_IDX = 8;
inline constexpr std::size_t COST_IDX = 9;
inline constexpr std::size_t DATASIZE_IDX = 10;
inline constexpr std::size_t REQMSG_IDX = 11;
inline constexpr std::size_t RESPMSG_IDX = 12;

// 运行日志字段
inline constexpr std::size_t RUNTIME_FIELDS_SIZE = 8;
inline constexpr std::size_t MESSAGE_IDX = 7;

enum class LevelOption {
    INFO,
    DEBUG,
    WARN,
    ERROR,
    FATAL
};

std::optional<LevelOption> LevelOptionFromString(const std::string &str);

struct FailureLogInfo {
    // fields in general
    int64_t timestamp;
    LevelOption level;
    std::string filename;
    std::string functionName;
    int lineNo;
    std::string podName;
    int pid;
    int tid;
    std::string traceId;
    std::string clusterName;

    std::vector<std::string> failureModeIds;
    std::string rawLog;

    FailureLogInfo(const std::vector<std::string> &fields, const std::string &rawLog);
    virtual ~FailureLogInfo() = default;
    void BindFailureMode(const std::string &failureModeId);
};

struct FailureLogInfoAccess : FailureLogInfo {
    // fields of access log
    int statusCode;
    std::string action;
    int cost;
    int dataSize;
    std::string reqMsg;
    std::string respMsg;

    FailureLogInfoAccess(const std::vector<std::string> &fields, const std::string &rawLog);
};

struct FailureLogInfoRuntime : FailureLogInfo {
    // fields of runtime log
    std::string message;

    FailureLogInfoRuntime(const std::vector<std::string> &fields, const std::string &rawLog);
};
} // namespace diag

#endif
