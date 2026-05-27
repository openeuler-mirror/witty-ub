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

#define MODULE_NAME "VIEW_VISUALIZER"

#include "view_visualizer_module.h"

#include "logger.h"
#include "ubse_context.h"

namespace view_visualizer {
using namespace ubse::context;

ViewVisualizerModule::ViewVisualizerModule() {}

RackResult ViewVisualizerModule::Initialize()
{
    visualizer_ = std::make_shared<ViewVisualizer>();
    auto res = visualizer_->Initialize();
    if (res != RACK_OK) {
        LOG_ERROR << "failed to initialize ViewVisualizerModule";
        return res;
    }
    LOG_DEBUG << "ViewVisualizerModule initialized";
    return res;
}

void ViewVisualizerModule::UnInitialize()
{
    visualizer_->UnInitialize();
}

RackResult ViewVisualizerModule::Start()
{
    auto res = visualizer_->Start();
    if (res != RACK_OK) {
        LOG_ERROR << "failed to start ViewVisualizerModule";
        return res;
    }
    LOG_DEBUG << "ViewVisualizerModule started";
    return res;
}

void ViewVisualizerModule::Stop()
{
    visualizer_->Stop();
}

std::shared_ptr<ViewVisualizer> ViewVisualizerModule::GetViewVisualizer() const
{
    return visualizer_;
}
} // namespace view_visualizer