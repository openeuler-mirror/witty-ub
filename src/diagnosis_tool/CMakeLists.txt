## Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 # witty-ub is licensed under the Mulan PSL v2.
 # You can use this software according to the terms and conditions of the Mulan PSL v2.
 # You may obtain a copy of Mulan PSL v2 at:
 #     http://license.coscl.org.cn/MulanPSL2
 # THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 # IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 # PURPOSE.
## See the Mulan PSL v2 for more details.

add_library(diagnosis_tool STATIC
    diagnosis_tool_module.cpp
    failure_mode_controller.cpp
    failure_mode_factory.cpp
    failure_mode.cpp
    failure_mode_realization/connect_break.cpp
    failure_mode_realization/hw_break.cpp
    failure_mode_realization/hw003_break.cpp
    failure_mode_realization/hw004_break.cpp
    failure_mode_realization/hw005_break.cpp
)
target_include_directories(diagnosis_tool PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(diagnosis_tool PUBLIC include ubse_context)
