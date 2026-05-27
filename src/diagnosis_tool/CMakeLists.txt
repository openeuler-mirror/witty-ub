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
    failure_mode_realization/kvcache/kvcache_conn_fault_001.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_002.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_002_001.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_002_002.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_002_003.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_002_004.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_002_005.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_002_006.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_002_007.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_002_008.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_006.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_006_001.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_006_002.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_006_003.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_007.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_008.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_009.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_010.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_011.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_012.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_012_001.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_012_002.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_012_003.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_012_004.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_020.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_020_001.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_020_002.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_020_003.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_020_004.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_020_005.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_020_006.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_020_007.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_020_008.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_020_009.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_020_010.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_028.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_028_001.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_028_002.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_028_003.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_028_004.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_028_005.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_028_006.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_028_007.cpp
    failure_mode_realization/kvcache/kvcache_conn_fault_028_008.cpp
    failure_mode_realization/urma/urma_log_helper.cpp
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
