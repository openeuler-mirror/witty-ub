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

#define MODULE_NAME "WITTY-UB-BRPC-DIAG"

#include <cstddef>
#include <cstdint>
#include <iostream>
#include <memory>
#include <string>
#include <typeindex>
#include <unordered_map>
#include <vector>

#include "diagnosis_module.h"
#include "logger.h"
#include "time_utils.h"
#include "ubse_context.h"

using namespace brpc;
using namespace ubse::context;

namespace {
constexpr size_t DATETIME_LENGTH = 19;
constexpr size_t INDEX_0 = 0;
constexpr size_t INDEX_4 = 4;
constexpr size_t INDEX_5 = 5;
constexpr size_t INDEX_7 = 7;
constexpr size_t INDEX_8 = 8;
constexpr size_t INDEX_10 = 10;
constexpr size_t INDEX_11 = 11;
constexpr size_t INDEX_13 = 13;
constexpr size_t INDEX_14 = 14;
constexpr size_t INDEX_16 = 16;
constexpr size_t INDEX_17 = 17;
constexpr size_t COUNT_2 = 2;
constexpr size_t COUNT_4 = 4;

UbseContext &g_rackContext = UbseContext::GetInstance();

// Parse an explicitly UTC+8 datetime and return a microsecond Unix timestamp.
// The input has no fractional-second field, so the microsecond part is always zero.
bool ParseUtc8Datetime(const std::string &value, int64_t &timestamp)
{
    if (value.size() != DATETIME_LENGTH || value[INDEX_4] != '-' || value[INDEX_7] != '-' || value[INDEX_10] != ' ' ||
        value[INDEX_13] != ':' || value[INDEX_16] != ':') {
        return false;
    }

    time::CivilTime parsed;
    if (!time::ParseFixedInt(value, INDEX_0, COUNT_4, parsed.year) ||
        !time::ParseFixedInt(value, INDEX_5, COUNT_2, parsed.month) ||
        !time::ParseFixedInt(value, INDEX_8, COUNT_2, parsed.day) ||
        !time::ParseFixedInt(value, INDEX_11, COUNT_2, parsed.hour) ||
        !time::ParseFixedInt(value, INDEX_14, COUNT_2, parsed.minute) ||
        !time::ParseFixedInt(value, INDEX_17, COUNT_2, parsed.second)) {
        return false;
    }
    return time::BuildUtc8Timestamp(parsed, timestamp);
}

bool ConvertTimeArgument(std::vector<std::string> &arguments)
{
    for (size_t i = 1; i < arguments.size(); ++i) {
        if (arguments[i] != "--time") {
            continue;
        }
        if (i + 1 >= arguments.size()) {
            std::cerr << "missing value for --time, expected YYYY-MM-DD HH:MM:SS\n";
            return false;
        }
        int64_t timestamp = 0;
        if (!ParseUtc8Datetime(arguments[i + 1], timestamp)) {
            std::cerr << "invalid --time value: " << arguments[i + 1]
                      << ", expected UTC+8 time in YYYY-MM-DD HH:MM:SS format\n";
            return false;
        }
        arguments[i] = "--timestamp";
        arguments[i + 1] = std::to_string(timestamp);
        ++i;
    }
    return true;
}

void RegisterModules()
{
    g_rackContext.RegisterModule<DiagnosisModule>();
}

void InitDependencies()
{
    g_rackContext.AddModuleDependencies<DiagnosisModule>();
}

std::vector<std::type_index> CreateModules()
{
    std::vector<std::type_index> sortedModules = g_rackContext.GetSortedModules();
    for (auto type : sortedModules) {
        LOG_DEBUG << "UbseContext::CreateModules: Creating module " << type.name();
        if (type == typeid(DiagnosisModule)) {
            g_rackContext.InitModule<DiagnosisModule>(RackModule::CreateModule<DiagnosisModule>());
        } else {
            LOG_ERROR << "CreateModule-Error: module " << type.name() << " not defined";
        }
    }
    return sortedModules;
}

void StopAndUnInitializeModules(const std::vector<std::type_index> &sortedModules)
{
    std::unordered_map<std::type_index, std::shared_ptr<RackModule>> moduleMap = g_rackContext.GetModuleMap();
    std::vector<std::shared_ptr<RackModule>> reverseOrderedModules;
    reverseOrderedModules.reserve(sortedModules.size());
    for (auto it = sortedModules.rbegin(); it != sortedModules.rend(); ++it) {
        auto moduleIt = moduleMap.find(*it);
        if (moduleIt != moduleMap.end()) {
            reverseOrderedModules.push_back(moduleIt->second);
        }
    }
    for (const auto &module : reverseOrderedModules) {
        module->Stop();
    }
    for (const auto &module : reverseOrderedModules) {
        module->UnInitialize();
    }
}
} // namespace

int main(int argc, char *argv[])
{
    std::vector<std::string> parsedArgv(argv, argv + argc);
    if (!ConvertTimeArgument(parsedArgv)) {
        return RACK_FAIL;
    }
    for (size_t i = 0; i < parsedArgv.size(); ++i) {
        argv[i] = parsedArgv[i].data();
    }

    rack::logger::init(argv[0]);
    InitDependencies();
    RackResult ret = g_rackContext.ParseArgs(argc, argv);
    if (ret == RACK_OK) {
        RegisterModules();
        const std::vector<std::type_index> sortedModules = CreateModules();
        ret = g_rackContext.Run(argc, argv);
        StopAndUnInitializeModules(sortedModules);
    }
    rack::logger::shutdown();
    return ret;
}
