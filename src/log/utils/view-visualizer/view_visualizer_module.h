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

#ifndef VIEW_VISUALIZER_MODULE_H
#define VIEW_VISUALIZER_MODULE_H

#include "rack_error.h"
#include "rack_module.h"
#include "view_visualizer.h"

namespace view_visualizer {
using namespace rack::module;

class ViewVisualizerModule final : public RackModule {
public:
    ViewVisualizerModule();
    ~ViewVisualizerModule() override = default;

    RackResult Initialize() override;
    void UnInitialize() override;
    RackResult Start() override;
    void Stop() override;

    std::shared_ptr<ViewVisualizer> GetViewVisualizer() const;

private:
    std::shared_ptr<ViewVisualizer> visualizer_;
};
} // namespace view_visualizer

#endif // VIEW_VISUALIZER_MODULE_H