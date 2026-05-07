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
#pragma once

#include <string>
#include <vector>

namespace brpc {
using namespace std;

// 系统日志结构体，用于存储系统日志的路径和内容
class SystemLog {
public:
    static string logPath; // 系统日志文件路径
    string text;           // 单条日志文本内容
};

// BRPC日志结构体，用于存储BRPC日志的路径和内容
class BrpcLog {
public:
    static string logPath; // BRPC日志文件路径
    string text;           // 单条日志文本内容
};

}
#endif
/*
    规范：在本文件中定义日志类，日志类对象可以表示一条日志，也可以进一步封装多条日志。
    日志类对象中可以实现日志检索、字段提取等功能。本样例实现了简单的单条日志定义。
    在类的定义前需要添加对该类表示什么类型的日志的注释，需要和定界文档中"故障现象"字段中对日志来源的描述相对应。
*/
