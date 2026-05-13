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

#ifndef VIEW_VISUALIZER_H
#define VIEW_VISUALIZER_H

#include <string>

#include <json/json.h>

#include "rack_error.h"

namespace view_visualizer {
class ViewVisualizer {
public:
    RackResult Initialize();
    void UnInitialize();
    RackResult Start();
    void Stop();

private:
    RackResult LoadView(Json::Value &root) const;
    RackResult WriteHtml(const std::string &html) const;
    RackResult ReadResourceFile(const std::string &fileName, std::string &content) const;
    std::string BuildHtml(const Json::Value &root) const;
};
} // namespace view_visualizer

#endif // VIEW_VISUALIZER_H
