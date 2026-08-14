## Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 # witty-ub is licensed under the Mulan PSL v2.
 # You can use this software according to the terms and conditions of the Mulan PSL v2.
 # You may obtain a copy of Mulan PSL v2 at:
 #     http://license.coscl.org.cn/MulanPSL2
 # THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 # IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 # PURPOSE.
## See the Mulan PSL v2 for more details.

project (witty-UB VERSION 0.0.1)
add_compile_definitions(
    PROJECT_VERSION="${PROJECT_VERSION}"
)
option(ENABLE_DAEMON_FEATURE "Enable daemon feature" OFF)
option(ENABLE_TOOL_FEATURE "Enable tool feature" ON)
# 如果启用了该选项，向编译器传递宏定义
if(ENABLE_DAEMON_FEATURE)
    add_compile_definitions(ENABLE_DAEMON_FEATURE)
endif()
if(ENABLE_TOOL_FEATURE)
    add_compile_definitions(ENABLE_TOOL_FEATURE)
endif()

add_subdirectory(include)
add_subdirectory(framework)
add_subdirectory(topology)
add_subdirectory(plugins)
add_subdirectory(log)
add_subdirectory(brpc_diag_tool)
add_subdirectory(diagnosis_tool)

#add_executable(copilot-worker
#    ubse_main.cpp
    # framework/database/database_module.cpp
    # topology/node_global_collector_module.cpp
    # topology/node_local_collector_module.cpp
#)
#target_include_directories(copilot-worker PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
#target_link_libraries(copilot-worker PRIVATE database ubse_context topology lcne obmm failure_log rack_http)

add_executable(witty-ub-log
    witty_ub_log_main.cpp
)
target_include_directories(witty-ub-log PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(witty-ub-log PRIVATE ubse_context failure_log rack_http)

add_executable(witty-ub-topo
    witty_ub_topo_main.cpp
)
target_include_directories(witty-ub-topo PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(witty-ub-topo PRIVATE ubse_context topology lcne rack_http urma witty_json)

add_executable(witty-ub-diag-tool
    witty_ub_diag_tool_main.cpp
)
target_include_directories(witty-ub-diag-tool PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
if(APPLE)
    target_link_options(witty-ub-diag-tool PRIVATE -force_load $<TARGET_FILE:diagnosis_tool>)
else()
    target_link_options(witty-ub-diag-tool PRIVATE 
        "-Wl,--whole-archive" 
        "$<TARGET_FILE:diagnosis_tool>"
        "-Wl,--no-whole-archive"
    )
endif()
target_link_libraries(witty-ub-diag-tool PRIVATE ubse_context diagnosis_tool log4cplus)

add_executable(witty-ub-brpc-diag
    witty_ub_brpc_diag_main.cpp
)
target_include_directories(witty-ub-brpc-diag PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(witty-ub-brpc-diag PRIVATE brpc_diag_tool)

add_executable(util-code-analyzer
    util_code_analyzer_main.cpp
)
target_include_directories(util-code-analyzer PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(util-code-analyzer PRIVATE ubse_context code_analyzer rack_http)

add_executable(util-view-visualizer
    util_view_visualizer_main.cpp
)
target_include_directories(util-view-visualizer PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(util-view-visualizer PRIVATE ubse_context view_visualizer)
