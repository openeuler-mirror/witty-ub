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

#define MODULE_NAME "DIAGNOSIS"

#include "diagnosis_tool_module.h"
#include <json/json.h>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include "failure_mode.h"
#include "failure_mode_controller.h"
#include "failure_mode_factory.h"
#include "failure_mode_realization/urma/urma_log_helper.h"
#include "failure_mode_view.h"
#include "logger.h"
#include "ubse_context.h"

namespace diag {
using namespace ubse::context;

DiagnosisToolModule::DiagnosisToolModule() {}

static std::vector<FailureModeController> visited;
static std::vector<std::vector<FailureModeController>> validRoutes;
constexpr const char *MODULE_KVCACHE = "kvcache_conn";
constexpr const char *MODULE_URMA = "urma";
constexpr const char *DEFAULT_WITTY_DIR = "/var/witty-ub";
constexpr const char *FAILUREMODE_JSON_DIR = "data/failure_mode_tree.json";
// 读取json文件，获取故障树
void DiagnosisToolModule::InitializeFailureModeTree()
{
    // 1. 清空现有数据
    failureModeJson.clear();

    // 2. 尝试打开文件
    const char *wittyDirEnv = std::getenv("WITTY_DIR");
    std::string wittyDir = wittyDirEnv ? wittyDirEnv : DEFAULT_WITTY_DIR;
    std::string path = (std::filesystem::path(wittyDir) / FAILUREMODE_JSON_DIR).string();
    std::ifstream file;
    file.open(path);
    if (!file.is_open()) {
        std::cerr << "Failed to open file: " << path << std::endl;
        return;
    }

    // 3. 解析 JSON
    Json::Value root;
    Json::CharReaderBuilder builder;
    std::string errs;
    if (!Json::parseFromStream(builder, file, &root, &errs)) {
        std::cerr << "Failed to parse JSON: " << errs << std::endl;
        return;
    }

    // 4. 遍历 JSON 并填充到 FailureModeJson
    auto outerKeys = root.getMemberNames();
    for (const auto &outerKey : outerKeys) {
        const Json::Value &innerObj = root[outerKey];
        if (!innerObj.isObject())
            continue;
        std::unordered_map<std::string, std::vector<std::string>> innerMap;
        auto innerKeys = innerObj.getMemberNames();
        std::unordered_set<std::string> allFailureModes, nonSubRootFailureModes;
        std::vector<std::string> subRootFailureModes;
        for (const auto &innerKey : innerKeys) {
            allFailureModes.insert(innerKey);
            failureModeInstanceMap[innerKey] = FailureModeFactory::Instance().Create(innerKey);
            const Json::Value &arrayValue = innerObj[innerKey];
            std::vector<std::string> vec;
            if (arrayValue.isArray()) {
                for (const auto &element : arrayValue) {
                    if (element.isString()) {
                        vec.push_back(element.asString());
                        nonSubRootFailureModes.insert(element.asString());
                        failureModeInstanceMap[innerKey]->AddSubFailureMode(element.asString());
                    }
                }
            }
            innerMap[innerKey] = vec;
        }
        for (std::string failureMode : allFailureModes) {
            if (nonSubRootFailureModes.find(failureMode) == nonSubRootFailureModes.end()) {
                subRootFailureModes.push_back(failureMode);
            }
        }
        subRootFailureModesMap[outerKey] = subRootFailureModes;
        failureModeJson[outerKey] = innerMap;
    }

    // 可选：输出成功信息
    std::cout << "Successfully loaded " << failureModeJson.size()
              << " outer keys from failure_mode_tree.json (path: " << path << ")" << std::endl;
}

// 初始化模块
RackResult DiagnosisToolModule::Initialize()
{
    InitializeFailureModeTree();
    return RACK_OK;
}

void DiagnosisToolModule::UnInitialize()
{
    LOG_INFO << "DiagnosisToolModule uninitialized";
}

bool DiagnosisToolModule::VisitKvCache(FailureModeController controller)
{
    bool isValid = controller.GetFailureMode()->IsValid();
    if (!isValid) {
        return false;
    }
    visited.push_back(controller);
    RootCause rootCause = controller.GetFailureMode()->AnalyzeRootCause();
    if (rootCause.GetIsFinalRootCause()) {
        validRoutes.push_back(visited);
    } else {
        bool nonValidFlag = true;
        for (std::string subFailureMode : controller.GetFailureMode()->GetSubFailureModes()) {
            if (VisitKvCache(FailureModeController(failureModeInstanceMap[subFailureMode]))) {
                nonValidFlag = false;
            }
        }
        if (nonValidFlag) {
            validRoutes.push_back(visited);
        }
    }
    visited.pop_back();
    return true;
}

bool DiagnosisToolModule::VisitUrma(FailureModeController controller)
{
    std::shared_ptr<FailureMode> failureMode = controller.GetFailureMode();
    std::string failureModeId = failureMode->GetId();
    if (failureMode->IsValid()) {
        const std::vector<FailureLogInfo> &logInfos =
            urma_log_helper::GetParsedFailureLogLines(failureMode->GetFailureLogInfoCache());
        for (FailureLogInfo logInfo : logInfos) {
            if (!logInfo.traceId.empty()) {
                controller.AddHitCount();
                logInfo.failureModeId = failureModeId;
                controller.AddLogInfo(logInfo);
                traces[logInfo.traceId].push_back(logInfo);
            }
        }
    }
    
    allFailureModes.insert(failureModeId);
    failureModeIdToController.emplace(failureModeId, controller);
    visited.push_back(controller);
    RootCause rootCause = failureMode->AnalyzeRootCause();
    if (!rootCause.GetIsFinalRootCause()) {
        for (std::string subFailureModeId : failureMode->GetSubFailureModes()) {
            VisitUrma(FailureModeController(failureModeInstanceMap[subFailureModeId]));
        }
    }
    visited.pop_back();
    return true;
}

void DiagnosisToolModule::StartKvcache(const std::vector<std::string> &subRootFailureModes)
{
    for (auto subRootFailureModeId : subRootFailureModes) {
        std::shared_ptr<FailureMode> subRootFailureMode = failureModeInstanceMap[subRootFailureModeId];
        VisitKvCache(FailureModeController(subRootFailureMode));
    }
    for (std::vector<FailureModeController> route : validRoutes) {
        bool isFirst = true;
        for (FailureModeController controller : route) {
            if (!isFirst) {
                std::cout << "->";
            }
            isFirst = false;
            std::cout << controller.GetFailureMode()->GetName();
        }
        std::cout << std::endl;
    }
}

void DiagnosisToolModule::StartUrma(const std::vector<std::string> &subRootFailureModes)
{
    for (auto subRootFailureModeId : subRootFailureModes) {
        std::shared_ptr<FailureMode> subRootFailureMode = failureModeInstanceMap[subRootFailureModeId];
        VisitUrma(FailureModeController(subRootFailureMode));
    }
    for (auto &[traceId, trace] : traces) {
        std::sort(trace.begin(), trace.end(), [](const FailureLogInfo &left, const FailureLogInfo &right) {
            return left.timestamp > right.timestamp;
        });
    }
    for (const auto &[traceId, trace] : traces) {
        int traceLen = trace.size();
        for (int i = 0; i < traceLen - 1; ++i) {
            const std::string &currModeId = trace[i].failureModeId;
            const std::string &nextModeId = trace[i + 1].failureModeId;
            auto &currController = failureModeIdToController.at(currModeId);
            currController.AddSubFailureModeValid(nextModeId);
            childFailureModes.insert(nextModeId);
        }
    }
    for (const auto &failureModeId : allFailureModes) {
        if (childFailureModes.find(failureModeId) == childFailureModes.end()) {
            rootFailureModes.insert(failureModeId);
        }
    }

    FailureModeView view;
    RackResult ret = view.Build(rootFailureModes, failureModeIdToController, traces);
    if (ret != RACK_OK) {
        LOG_ERROR << "failed to build failure mode view";
        return;
    }
    ret = view.Dump();
    if (ret != RACK_OK) {
        LOG_ERROR << "failed to dump failure mode view";
    }
}

RackResult DiagnosisToolModule::Start()
{
    for (auto subRootFailures : subRootFailureModesMap) {
        std::string moduleName = subRootFailures.first;
        std::cout << "Diagnosing failures in module: " << moduleName << std::endl;
        if (moduleName == MODULE_KVCACHE) {
            StartKvcache(subRootFailures.second);
        } else if (moduleName == MODULE_URMA) {
            StartUrma(subRootFailures.second);
        }
    }
    LOG_INFO << "DiagnosisToolModule::Start() - Completed";
    return RACK_OK;
}

void DiagnosisToolModule::Stop()
{
    LOG_INFO << "DiagnosisToolModule stopped";
}

} // namespace diag
