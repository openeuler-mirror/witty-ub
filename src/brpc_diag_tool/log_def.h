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

#ifndef LOG_DEF_H
#define LOG_DEF_H

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>

namespace brpc {

inline constexpr std::string_view URMA_COMPONENT = "URMA";
inline constexpr std::string_view URMA_LOG_PREFIX = "[URMA]";

// BRPC日志结构体，用于存储BRPC日志原文及从原文解析出的结构化字段
struct BrpcLog {
    std::string text;           // 单条日志原文，仅用于解析和稳定排序
    std::int64_t timestamp = 0; // 微秒级 Unix 时间戳（东八区输入已转 UTC）
    std::string podName;
    std::string podIp;
    std::string component;
    std::string filename;
    std::string functionName;
    int lineNo = 0;
    std::optional<int> threadId;
    std::optional<std::string> traceId;
    std::string message; // 仅去除 BRPC 日志头的正文；URMA 日志头保留，用于故障模式匹配并写入诊断结果
};

} // namespace brpc
/*
    规范：在本文件中定义日志类，日志类对象可以表示一条日志，也可以进一步封装多条日志。
    日志类对象中可以实现日志检索、字段提取等功能。本样例实现了简单的单条日志定义。
    在类的定义前需要添加对该类表示什么类型的日志的注释，需要和定界文档中"故障现象"字段中对日志来源的描述相对应。
*/

#endif // LOG_DEF_H