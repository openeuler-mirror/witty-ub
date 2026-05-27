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

#define MODULE_NAME "CODE_ANALYZER"

#include "code_analyzer_module.h"

#include "code_analyzer.h"
#include "logger.h"
#include "ubse_context.h"

namespace code_analyzer {
using namespace ubse::context;

CodeAnalyzerModule::CodeAnalyzerModule() {}

RackResult CodeAnalyzerModule::Initialize()
{
    analyzer_ = std::make_shared<CodeAnalyzer>();
    auto res = analyzer_->Initialize();
    if (res != RACK_OK) {
        LOG_ERROR << "failed to initialize CodeAnalyzerModule";
        return res;
    }
    LOG_DEBUG << "CodeAnalyzerModule initialized";
    return res;
}

void CodeAnalyzerModule::UnInitialize()
{
    analyzer_->UnInitialize();
}

RackResult CodeAnalyzerModule::Start()
{
    auto res = analyzer_->Start();
    if (res != RACK_OK) {
        LOG_ERROR << "failed to start CodeAnalyzerModule";
        return res;
    }
    LOG_DEBUG << "CodeAnalyzerModule started";
    return res;
}

void CodeAnalyzerModule::Stop()
{
    analyzer_->Stop();
}

std::shared_ptr<CodeAnalyzer> CodeAnalyzerModule::GetCodeAnalyzer() const
{
    return analyzer_;
}
} // namespace code_analyzer
