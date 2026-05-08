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
#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include "log_def.h"

namespace brpc {
using namespace std;

// 日志收集器，负责从文件中读取系统日志和BRPC日志
class LogCollector {
public:
    // 收集系统日志，根据时间戳筛选
    vector<SystemLog> CollectSystemLog(int64_t timestamp);
    // 收集BRPC日志，根据时间戳筛选
    vector<BrpcLog> CollectBrpcLog(int64_t timestamp);
};

} // namespace brpc
#endif
/*
    规范：在本文件中定义日志采集的实现逻辑。本样例实现了从系统日志和brpc日志样例中分别读取日志数据的功能。
*/
