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
#ifndef LOG_COLLECTOR_H
#define LOG_COLLECTOR_H

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include "log_def.h"

namespace brpc {
// 日志收集器，负责从文件中读取 BRPC 日志。
class LogCollector {
public:
    using BrpcLogConsumer = std::function<void(BrpcLog &&)>;

    explicit LogCollector(std::filesystem::path brpcLogPath);

    bool ForEachBrpcLog(std::int64_t startTimestamp, std::int64_t endTimestamp, const BrpcLogConsumer &consumer) const;

    static std::int64_t CurrentTimestamp();

private:
    struct UrmaLogFields {
        std::string filename;
        std::string functionName;
        int lineNo = 0;
        std::optional<int> threadId;
        std::optional<std::string> traceId;
    };

    static bool ParseNonnegativeInt(std::string_view value, int &result);
    static bool ParseLogTimestamp(std::string_view timestampText, std::int64_t &timestamp);
    static bool ParseLocation(std::string_view location, std::string &filename, std::string &functionName, int &lineNo);
    static bool ParseThreadId(std::string_view value, std::optional<int> &threadId);
    static bool ParseTraceId(std::string_view value, std::optional<std::string> &traceId);
    static bool ParseUrmaLogFields(std::string_view urmaText, UrmaLogFields &result);
    static bool ExtractLogTimestamp(std::string_view text, std::int64_t &timestamp);

    template <std::size_t FieldCount>
    static bool ExtractBracketFields(std::string_view text, std::array<std::string_view, FieldCount> &fields,
                                     std::size_t &offset);

    // 按 BRPC 日志格式将原文解析到结构化字段；timestamp 已在预筛选阶段写入 logEntry。
    static bool ParseBrpcLogFields(BrpcLog &logEntry);

    std::filesystem::path brpcLogPath_;
};

} // namespace brpc
/*
    规范：在本文件中定义日志采集的实现逻辑。
*/

#endif // LOG_COLLECTOR_H
