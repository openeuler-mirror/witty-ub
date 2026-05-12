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
    failure_mode_realization/hw_break003.cpp
    failure_mode_realization/hw_break004.cpp
    failure_mode_realization/hw_break005.cpp
    failure_mode_realization/kvcache_conn_fault_001.cpp
    failure_mode_realization/kvcache_conn_fault_002.cpp
    failure_mode_realization/kvcache_conn_fault_003.cpp
    failure_mode_realization/kvcache_conn_fault_004.cpp
    failure_mode_realization/kvcache_conn_fault_005.cpp
    failure_mode_realization/kvcache_conn_fault_006.cpp
    failure_mode_realization/kvcache_conn_fault_007.cpp
    failure_mode_realization/kvcache_conn_fault_008.cpp
    failure_mode_realization/kvcache_conn_fault_009.cpp
    failure_mode_realization/kvcache_conn_fault_010.cpp
    failure_mode_realization/kvcache_conn_fault_011.cpp
    failure_mode_realization/kvcache_conn_fault_012.cpp
    failure_mode_realization/kvcache_conn_fault_013.cpp
    failure_mode_realization/kvcache_conn_fault_014.cpp
    failure_mode_realization/kvcache_conn_fault_015.cpp
    failure_mode_realization/kvcache_conn_fault_016.cpp
    failure_mode_realization/kvcache_conn_fault_017.cpp
    failure_mode_realization/kvcache_conn_fault_018.cpp
    failure_mode_realization/kvcache_conn_fault_019.cpp
    failure_mode_realization/kvcache_conn_fault_020.cpp
    failure_mode_realization/kvcache_conn_fault_021.cpp
    failure_mode_realization/kvcache_conn_fault_022.cpp
    failure_mode_realization/kvcache_conn_fault_023.cpp
    failure_mode_realization/kvcache_conn_fault_024.cpp
    failure_mode_realization/kvcache_conn_fault_025.cpp
    failure_mode_realization/kvcache_conn_fault_026.cpp
    failure_mode_realization/kvcache_conn_fault_027.cpp
    failure_mode_realization/kvcache_conn_fault_028.cpp
    failure_mode_realization/kvcache_conn_fault_029.cpp
    failure_mode_realization/kvcache_conn_fault_030.cpp
    failure_mode_realization/kvcache_conn_fault_031.cpp
    failure_mode_realization/kvcache_conn_fault_032.cpp
    failure_mode_realization/kvcache_conn_fault_033.cpp
    failure_mode_realization/kvcache_conn_fault_034.cpp
    failure_mode_realization/kvcache_conn_fault_035.cpp
    failure_mode_realization/kvcache_conn_fault_036.cpp
    failure_mode_realization/kvcache_conn_fault_037.cpp
    failure_mode_realization/kvcache_conn_fault_038.cpp
    failure_mode_realization/kvcache_conn_fault_039.cpp
    failure_mode_realization/kvcache_conn_fault_040.cpp
    failure_mode_realization/kvcache_conn_fault_041.cpp
    failure_mode_realization/kvcache_conn_fault_042.cpp
    failure_mode_realization/kvcache_conn_fault_043.cpp
    failure_mode_realization/kvcache_conn_fault_044.cpp
    failure_mode_realization/kvcache_conn_fault_045.cpp
    failure_mode_realization/kvcache_conn_fault_046.cpp
    failure_mode_realization/kvcache_conn_fault_047.cpp
    failure_mode_realization/kvcache_conn_fault_048.cpp
    failure_mode_realization/kvcache_conn_fault_049.cpp
    failure_mode_realization/kvcache_conn_fault_050.cpp
)
target_include_directories(diagnosis_tool PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
find_package(jsoncpp QUIET)
if(jsoncpp_FOUND)
    target_link_libraries(diagnosis_tool PUBLIC include ubse_context jsoncpp_lib)
else()
    target_include_directories(diagnosis_tool PUBLIC /usr/include/jsoncpp)
    target_link_libraries(diagnosis_tool PUBLIC include ubse_context -ljsoncpp -lstdc++fs)
endif()
