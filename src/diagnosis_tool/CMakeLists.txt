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
    diagnosis_engine.cpp
    failure_log_helper.cpp
    failure_log_info.cpp
    failure_mode_controller.cpp
    failure_mode_view.cpp
    failure_mode.cpp
)
target_include_directories(diagnosis_tool PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

find_package(jsoncpp QUIET)
find_library(RE2_LIBRARY NAMES re2 REQUIRED)

if(jsoncpp_FOUND)
    target_link_libraries(diagnosis_tool
        PUBLIC
            include
            ubse_context
            jsoncpp_lib
            ${RE2_LIBRARY}
    )
else()
    target_include_directories(diagnosis_tool PUBLIC /usr/include/jsoncpp)
    target_link_libraries(diagnosis_tool
        PUBLIC
            include
            ubse_context
            jsoncpp
            stdc++fs
            ${RE2_LIBRARY}
    )
endif()
