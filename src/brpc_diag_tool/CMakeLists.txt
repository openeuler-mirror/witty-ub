## Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 # witty-ub is licensed under the Mulan PSL v2.
 # You can use this software according to the terms and conditions of the Mulan PSL v2.
 # You may obtain a copy of Mulan PSL v2 at:
 #     http://license.coscl.org.cn/MulanPSL2
 # THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 # IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 # PURPOSE.
## See the Mulan PSL v2 for more details.

add_library(brpc_diag_tool STATIC
    time_utils.cpp
    log_collector.cpp
    diagnosis_result.cpp
    diagnosis_engine.cpp
    diagnosis_module.cpp
)
target_include_directories(brpc_diag_tool PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

find_package(jsoncpp QUIET)
find_package(OpenSSL REQUIRED)

if(jsoncpp_FOUND)
    target_link_libraries(brpc_diag_tool
        PUBLIC
            include
            ubse_context
        PRIVATE
            jsoncpp_lib
            OpenSSL::Crypto
    )
else()
    target_include_directories(brpc_diag_tool PRIVATE /usr/include/jsoncpp)
    target_link_libraries(brpc_diag_tool
        PUBLIC
            include
            ubse_context
        PRIVATE
            jsoncpp
            OpenSSL::Crypto
    )
endif()
