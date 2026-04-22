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

#pragma once

#include <string>

namespace brpc {
using namespace std;
class DiagnosisResult {
public:
    string result;
    void OutputResult();
};
}

/*
    规范：在本文件中定义诊断结果类型，即DiagnosisEngine.diagnosis的返回值类型。主要包含:
    1、数据：诊断结果数据，本样例中为字符串result；
    2、输出函数：输出诊断结果，会在结束诊断后被调用，本样例中在OutputResult中定义，打印result。
*/
