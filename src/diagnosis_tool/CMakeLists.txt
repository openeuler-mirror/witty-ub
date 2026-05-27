## Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 # witty-ub is licensed under the Mulan PSL v2.
 # You can use this software according to the terms and conditions of the Mulan PSL v2.
 # You may obtain a copy of Mulan PSL v2 at:
 #     http://license.coscl.org.cn/MulanPSL2
 # THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 # IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 # PURPOSE.
## See the Mulan PSL v2 for more details.

file(GLOB URMA_FAILURE_MODE_SOURCES failure_mode_realization/urma/urma_failure_*.cpp)
file(GLOB KVCACHE_FAILURE_MODE_SOURCES failure_mode_realization/kvcache/kvcache_conn_fault_*.cpp)

add_library(diagnosis_tool STATIC
    diagnosis_tool_module.cpp
    failure_mode_controller.cpp
    failure_mode_factory.cpp
    failure_mode.cpp
    failure_mode_view.cpp
    failure_mode_realization/connect_break.cpp
    failure_mode_realization/hw_break.cpp
    failure_mode_realization/hw_break003.cpp
    failure_mode_realization/hw_break004.cpp
    failure_mode_realization/hw_break005.cpp
    failure_mode_realization/kvcache/kvcache_log_helper.cpp
    failure_mode_realization/urma/urma_log_helper.cpp
    ${KVCACHE_FAILURE_MODE_SOURCES}
    ${URMA_FAILURE_MODE_SOURCES}
)
target_include_directories(diagnosis_tool PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
find_package(jsoncpp QUIET)
if(jsoncpp_FOUND)
    target_link_libraries(diagnosis_tool PUBLIC include ubse_context jsoncpp_lib)
else()
    target_include_directories(diagnosis_tool PUBLIC /usr/include/jsoncpp)
    target_link_libraries(diagnosis_tool PUBLIC include ubse_context -ljsoncpp -lstdc++fs)
endif()
