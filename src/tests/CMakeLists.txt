# GTest/GMock 由系统 RPM 提供（openEuler: gtest-devel / gmock-devel）
find_package(GTest REQUIRED)
include(GoogleTest)

# Helper function to add a test target
function(witty_add_test target_name source_file)
    add_executable(${target_name} ${source_file})
    target_include_directories(${target_name} PRIVATE
        ${CMAKE_SOURCE_DIR}/src
        ${CMAKE_SOURCE_DIR}/src/include
        ${CMAKE_SOURCE_DIR}/src/brpc_diag_tool
        ${CMAKE_SOURCE_DIR}/src/diagnosis_tool
    )
    target_link_libraries(${target_name} PRIVATE ${ARGN} GTest::gtest_main)
    gtest_discover_tests(${target_name})
endfunction()

# C++ test targets
witty_add_test(test_failure_log_helper test_failure_log_helper.cpp diagnosis_tool)
witty_add_test(test_time_utils test_time_utils.cpp brpc_diag_tool)
witty_add_test(test_failure_mode test_failure_mode.cpp diagnosis_tool)
witty_add_test(test_failure_mode_controller test_failure_mode_controller.cpp diagnosis_tool)
witty_add_test(test_failure_log_info test_failure_log_info.cpp diagnosis_tool)
witty_add_test(test_diagnosis_engine test_diagnosis_engine.cpp brpc_diag_tool)
witty_add_test(test_diagnosis_result test_diagnosis_result.cpp brpc_diag_tool)
witty_add_test(test_node_data_def test_node_data_def.cpp include)
witty_add_test(test_failure_def test_failure_def.cpp include)

# B2：A 级直测目标
witty_add_test(test_log_template test_log_template.cpp failure_log)
witty_add_test(test_log_parser test_log_parser.cpp failure_log)
witty_add_test(test_log_reader test_log_reader.cpp failure_log)
witty_add_test(test_urma_topology test_urma_topology.cpp urma)
witty_add_test(test_lcne test_lcne.cpp lcne)
witty_add_test(test_database test_database.cpp database log4cplus)
witty_add_test(test_ubse_context test_ubse_context.cpp ubse_context)

# B3：B 级目标
witty_add_test(test_log_collector test_log_collector.cpp failure_log)
witty_add_test(test_log_graph test_log_graph.cpp failure_log)
witty_add_test(test_log_view test_log_view.cpp failure_log)
witty_add_test(test_node_collector test_node_collector.cpp topology)
witty_add_test(test_witty_json test_witty_json.cpp witty_json)
witty_add_test(test_rack_http test_rack_http.cpp rack_http)
witty_add_test(test_code_analyzer test_code_analyzer.cpp code_analyzer)
witty_add_test(test_view_visualizer test_view_visualizer.cpp view_visualizer)

# B4：C 级浅测目标
witty_add_test(test_rack_http_client test_rack_http_client.cpp rack_http log4cplus)
witty_add_test(test_module_shells test_module_shells.cpp
    failure_log topology urma lcne database witty_json log4cplus)

# B5：覆盖率补齐目标
witty_add_test(test_diagnosis_tool_engine test_diagnosis_tool_engine.cpp diagnosis_tool)
witty_add_test(test_diagnosis_tool_module test_diagnosis_tool_module.cpp diagnosis_tool)
witty_add_test(test_brpc_log_collector test_brpc_log_collector.cpp brpc_diag_tool)
