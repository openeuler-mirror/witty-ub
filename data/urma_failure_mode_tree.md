# URMA故障模式树

## 1 初始化失败
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 1.1 初始化URMA资源所需输入对象无效导致初始化端口失败
* 故障编号：urma_001
* 故障现象：
    * 关键日志：匹配`init_active_indices`，匹配`Invalid port_count:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化端口，调用方传入的初始化URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：init_active_indices
#### 1.2 初始化URMA资源所需输入对象无效导致激活端口失败
* 故障编号：urma_002
* 故障现象：
    * 关键日志：匹配`init_active_indices`，匹配`Invalid active port id, value: 0x`，匹配`x.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活端口，调用方传入的初始化URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：init_active_indices
#### 1.3 未找到可用于初始化端口的有效对象或路由
* 故障编号：urma_003
* 故障现象：
    * 关键日志：匹配`init_target_active_indices`，匹配`Failed to find connected port`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在初始化端口过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位目标。
* 解决办法：无
* 函数名：init_target_active_indices
#### 1.4 初始化JFS过程中依赖步骤失败
* 故障编号：urma_004
* 故障现象：
    * 关键日志：匹配`bondp_del_jfs_p_vjetty_info`，匹配`Failed to init active indices`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_del_jfs_p_vjetty_info
#### 1.5 JFS数据通路处理失败
* 故障编号：urma_005
* 故障现象：
    * 关键日志：匹配`bondp_del_jfs_p_vjetty_info`，匹配`Failed to init jfs wr buf`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_del_jfs_p_vjetty_info
#### 1.6 初始化JFR过程中依赖步骤失败
* 故障编号：urma_006
* 故障现象：
    * 关键日志：匹配`bondp_create_vjfr`，匹配`bondp init jfr fail:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_create_vjfr
#### 1.7 初始化JFR过程中依赖步骤失败
* 故障编号：urma_007
* 故障现象：
    * 关键日志：匹配`bondp_del_jfr_p_vjetty_info`，匹配`Failed to init active indices`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_del_jfr_p_vjetty_info
#### 1.8 JFR数据通路处理失败
* 故障编号：urma_008
* 故障现象：
    * 关键日志：匹配`bondp_del_jfr_p_vjetty_info`，匹配`Failed to init jfr wr buf`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_del_jfr_p_vjetty_info
#### 1.9 初始化Jetty过程中依赖步骤失败
* 故障编号：urma_009
* 故障现象：
    * 关键日志：匹配`bondp_del_jetty_p_vjetty_info`，匹配`Failed to init active indices`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_del_jetty_p_vjetty_info
#### 1.10 Jetty数据通路处理失败
* 故障编号：urma_010
* 故障现象：
    * 关键日志：匹配`bondp_del_jetty_p_vjetty_info`，匹配`Failed to init jetty send wr buf`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_del_jetty_p_vjetty_info
#### 1.11 Jetty数据通路处理失败
* 故障编号：urma_011
* 故障现象：
    * 关键日志：匹配`bondp_del_jetty_p_vjetty_info`，匹配`Failed to init jetty recv wr buf`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_del_jetty_p_vjetty_info
#### 1.12 初始化物理 Jetty过程中依赖步骤失败
* 故障编号：urma_012
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pjetty`，匹配`Failed to init active indices`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化物理 Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_unimport_pjetty
#### 1.13 初始化物理 Jetty过程中依赖步骤失败
* 故障编号：urma_013
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pjetty`，匹配`Failed to init target active indices`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化物理 Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_unimport_pjetty
#### 1.14 初始化物理 JFR过程中依赖步骤失败
* 故障编号：urma_014
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pjfr`，匹配`Failed to init active indices`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化物理 JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_unimport_pjfr
#### 1.15 初始化物理 JFR过程中依赖步骤失败
* 故障编号：urma_015
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pjfr`，匹配`Failed to init target active indices`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化物理 JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_unimport_pjfr
#### 1.16 初始化URMA资源过程中依赖步骤失败
* 故障编号：urma_016
* 故障现象：
    * 关键日志：匹配`bdp_v_conn_init`，匹配`Failed to init slide window in bdp_v_conn_table_add`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bdp_v_conn_init
#### 1.17 URMA context、provider操作表、JFS对象无效导致投递JFS失败
* 故障编号：urma_017
* 故障现象：
    * 关键日志：匹配`urma_write_affinity`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于投递JFS，调用方传入的URMA context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_write_affinity
#### 1.18 初始化健康检查过程中依赖步骤失败
* 故障编号：urma_018
* 故障现象：
    * 关键日志：匹配`bondp_create_health_check_ctx`，匹配`Failed to init health event lock`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化健康检查，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_create_health_check_ctx
#### 1.19 设备注册时下层资源准备失败
* 故障编号：urma_019
* 故障现象：
    * 关键日志：匹配`urma_provider_bond_init`，匹配`Provider Bond register ops failed.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责注册设备，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：urma_provider_bond_init
#### 1.20 URMA资源注册时下层资源准备失败
* 故障编号：urma_020
* 故障现象：
    * 关键日志：匹配`urma_provider_bond_uninit`，匹配`Provider Bond register ops not registered.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责注册URMA资源，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：urma_provider_bond_uninit
#### 1.21 context相关临时结构或命令参数分配失败
* 故障编号：urma_021
* 故障现象：
    * 关键日志：匹配`bondp_global_ctx_init`，匹配`Failed to alloc global context`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配context前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：bondp_global_ctx_init
#### 1.22 context创建时下层资源准备失败
* 故障编号：urma_022
* 故障现象：
    * 关键日志：匹配`bondp_init`，匹配`Failed to create global context.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_init
#### 1.23 初始化context过程中依赖步骤失败
* 故障编号：urma_023
* 故障现象：
    * 关键日志：匹配`bondp_init`，匹配`Failed to init bondp netlink context.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_init
#### 1.24 设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败
* 故障编号：urma_024
* 故障现象：
    * 关键日志：匹配`bondp_init`，匹配`Failed to start health check thread.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：bondp_init
#### 1.25 context清理阶段下层释放操作失败
* 故障编号：urma_025
* 故障现象：
    * 关键日志：匹配`bondp_uninit`，匹配`Failed to delete global context.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销context相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_uninit
#### 1.26 获取设备过程中依赖步骤失败
* 故障编号：urma_026
* 故障现象：
    * 关键日志：匹配`bondp_init_member_eid_info_list`，匹配`Failed to get slave device info`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_init_member_eid_info_list
#### 1.27 设备对象无效导致初始化设备失败
* 故障编号：urma_027
* 故障现象：
    * 关键日志：匹配`bondp_init_member_eid_info_list`，匹配`Invalid slave device number`，匹配`of device`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化设备，调用方传入的设备对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_init_member_eid_info_list
#### 1.28 获取设备过程中依赖步骤失败
* 故障编号：urma_028
* 故障现象：
    * 关键日志：匹配`bondp_init_member_eid_info_list`，匹配`Failed to get device by name`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_init_member_eid_info_list
#### 1.29 初始化端口过程中依赖步骤失败
* 故障编号：urma_029
* 故障现象：
    * 关键日志：匹配`bondp_create_pcontext`，匹配`Failed to init port info list`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化端口，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_create_pcontext
#### 1.30 删除context过程中依赖步骤失败
* 故障编号：urma_030
* 故障现象：
    * 关键日志：匹配`bondp_delete_pcontext`，匹配`Uninitialized variables`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_delete_pcontext
#### 1.31 初始化URMA资源所需输入对象无效导致初始化URMA资源失败
* 故障编号：urma_031
* 故障现象：
    * 关键日志：匹配`bdp_slide_wnd_init`，匹配`Invalid param wnd`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化URMA资源，调用方传入的初始化URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bdp_slide_wnd_init
#### 1.32 初始化URMA资源所需输入对象无效导致初始化URMA资源失败
* 故障编号：urma_032
* 故障现象：
    * 关键日志：匹配`bdp_slide_wnd_init`，匹配`Invalid param: total_size <= window_size`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化URMA资源，调用方传入的初始化URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bdp_slide_wnd_init
#### 1.33 初始化URMA资源过程中依赖步骤失败
* 故障编号：urma_033
* 故障现象：
    * 关键日志：匹配`bdp_slide_wnd_init`，匹配`Failed to init bitmap`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bdp_slide_wnd_init
#### 1.34 执行URMA资源所需输入对象无效导致释放URMA资源失败
* 故障编号：urma_034
* 故障现象：
    * 关键日志：匹配`bdp_slide_wnd_uninit`，匹配`Invalid param wnd`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放URMA资源，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bdp_slide_wnd_uninit
#### 1.35 初始化Jetty所需输入对象无效导致初始化Jetty失败
* 故障编号：urma_035
* 故障现象：
    * 关键日志：匹配`init_create_jetty_cmd`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化Jetty，调用方传入的初始化Jetty所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：init_create_jetty_cmd
#### 1.36 JFR对象无效导致初始化Jetty失败
* 故障编号：urma_036
* 故障现象：
    * 关键日志：匹配`init_create_jetty_cmd`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化Jetty，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：init_create_jetty_cmd
#### 1.37 Jetty初始化时下层资源准备失败
* 故障编号：urma_037
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_jetty`，匹配`failed to init create jetty cmd`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责初始化Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：urma_cmd_create_jetty
#### 1.38 Jetty相关临时结构或命令参数分配失败
* 故障编号：urma_038
* 故障现象：
    * 关键日志：匹配`urma_cmd_alloc_jetty`，匹配`failed to init alloc jetty cmd`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在初始化Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_cmd_alloc_jetty
#### 1.39 执行URMA资源过程中依赖步骤失败
* 故障编号：urma_039
* 故障现象：
    * 关键日志：匹配`urma_close_provider`，匹配`close failed, err:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_close_provider
#### 1.40 打开URMA资源过程中依赖步骤失败
* 故障编号：urma_040
* 故障现象：
    * 关键日志：匹配`urma_open_provider`，匹配`doesn't exist or doesn't have permission.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于打开URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_open_provider
#### 1.41 打开URMA资源过程中依赖步骤失败
* 故障编号：urma_041
* 故障现象：
    * 关键日志：匹配`urma_open_provider`，匹配`realpath failed.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于打开URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_open_provider
#### 1.42 设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败
* 故障编号：urma_042
* 故障现象：
    * 关键日志：匹配`urma_open_provider`，匹配`open failed, err:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_open_provider
#### 1.43 注册URMA资源所需输入对象无效导致注册URMA资源失败
* 故障编号：urma_043
* 故障现象：
    * 关键日志：匹配`urma_register_provider_ops`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于注册URMA资源，调用方传入的注册URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_register_provider_ops
#### 1.44 provider操作表无效导致注销URMA资源失败
* 故障编号：urma_044
* 故障现象：
    * 关键日志：匹配`urma_unregister_provider_ops`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于注销URMA资源，调用方传入的provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unregister_provider_ops
#### 1.45 设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败
* 故障编号：urma_045
* 故障现象：
    * 关键日志：匹配`urma_open_drivers`，匹配`Failed to open provider`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_open_drivers
#### 1.46 初始化URMA资源过程中依赖步骤失败
* 故障编号：urma_046
* 故障现象：
    * 关键日志：匹配`urma_init`，匹配`urma_init has been called before.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：查看/usr/lib64/urma目录下，是否存在liburma_udma.so等驱动文件，或查看文件是否具备x权限，完成正确部署后重试
* 函数名：urma_init
#### 1.47 URMA资源初始化时下层资源准备失败
* 故障编号：urma_047
* 故障现象：
    * 关键日志：匹配`urma_init`，匹配`None of the providers registered.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责初始化URMA资源，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：查看/usr/lib64/urma目录下，是否存在liburma_udma.so等驱动文件，或查看文件是否具备x权限，完成正确部署后重试
* 函数名：urma_init
#### 1.48 执行URMA资源所需输入对象无效导致释放设备失败
* 故障编号：urma_048
* 故障现象：
    * 关键日志：匹配`urma_uninit`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放设备，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_uninit
#### 1.49 初始化context过程中依赖步骤失败
* 故障编号：urma_049
* 故障现象：
    * 关键日志：匹配`urma_start_perf`，匹配`Urma perf failed to initialize performance record context`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_start_perf
#### 1.50 执行context过程中依赖步骤失败
* 故障编号：urma_050
* 故障现象：
    * 关键日志：匹配`urma_stop_perf`，匹配`Urma perf failed to uninitialize performance record context`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_stop_perf

## 2 建链失败
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 2.1 执行虚拟 JFS过程中依赖步骤失败
* 故障编号：urma_051
* 故障现象：
    * 关键日志：匹配`bondp_add_jfs_p_vjetty_id_info`，匹配`Failed to add p_vjfs_id[`，匹配`]: ret:`，匹配`, p_jfs_id:`，匹配`, v_jfs_id:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行虚拟 JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_add_jfs_p_vjetty_id_info
#### 2.2 虚拟 JFS清理阶段下层释放操作失败
* 故障编号：urma_052
* 故障现象：
    * 关键日志：匹配`bondp_del_jfs_p_vjetty_info_without_lock`，匹配`Failed to delete p_vjfs_id node[`，匹配`]: ret:`，匹配`pjfs_id:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销虚拟 JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_del_jfs_p_vjetty_info_without_lock
#### 2.3 组件创建时下层资源准备失败
* 故障编号：urma_053
* 故障现象：
    * 关键日志：匹配`bondp_del_jfs_p_vjetty_info`，匹配`Failed to create bondp comp`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建组件，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_del_jfs_p_vjetty_info
#### 2.4 物理 JFS创建时下层资源准备失败
* 故障编号：urma_054
* 故障现象：
    * 关键日志：匹配`bondp_del_jfs_p_vjetty_info`，匹配`Failed to create pjfs`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建物理 JFS，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_del_jfs_p_vjetty_info
#### 2.5 虚拟 JFS创建时下层资源准备失败
* 故障编号：urma_055
* 故障现象：
    * 关键日志：匹配`bondp_del_jfs_p_vjetty_info`，匹配`Failed to create vjfs`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建虚拟 JFS，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_del_jfs_p_vjetty_info
#### 2.6 创建JFS过程中依赖步骤失败
* 故障编号：urma_056
* 故障现象：
    * 关键日志：匹配`bondp_del_jfs_p_vjetty_info`，匹配`Failed to add jfs p_vjetty_id info`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_del_jfs_p_vjetty_info
#### 2.7 JFS创建时下层资源准备失败
* 故障编号：urma_057
* 故障现象：
    * 关键日志：匹配`bondp_del_jfs_p_vjetty_info`，匹配`Failed to create jfs datapath ctx`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建JFS，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_del_jfs_p_vjetty_info
#### 2.8 执行虚拟 JFR过程中依赖步骤失败
* 故障编号：urma_058
* 故障现象：
    * 关键日志：匹配`bondp_add_jfr_p_vjetty_id_info`，匹配`Failed to add p_vjfr_id[`，匹配`]: ret:`，匹配`, p_jfr_id:`，匹配`, v_jfr_id:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行虚拟 JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_add_jfr_p_vjetty_id_info
#### 2.9 虚拟 JFR清理阶段下层释放操作失败
* 故障编号：urma_059
* 故障现象：
    * 关键日志：匹配`bondp_del_jfr_p_vjetty_info_without_lock`，匹配`Failed to delete p_vjfr_id node[`，匹配`]: ret`，匹配`pjfr_id:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销虚拟 JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_del_jfr_p_vjetty_info_without_lock
#### 2.10 物理 JFR创建时下层资源准备失败
* 故障编号：urma_060
* 故障现象：
    * 关键日志：匹配`bondp_del_jfr_p_vjetty_info`，匹配`Failed to create pjfr`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建物理 JFR，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_del_jfr_p_vjetty_info
#### 2.11 虚拟 JFR创建时下层资源准备失败
* 故障编号：urma_061
* 故障现象：
    * 关键日志：匹配`bondp_del_jfr_p_vjetty_info`，匹配`Failed to create vjfr`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建虚拟 JFR，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_del_jfr_p_vjetty_info
#### 2.12 JFR创建时下层资源准备失败
* 故障编号：urma_062
* 故障现象：
    * 关键日志：匹配`bondp_del_jfr_p_vjetty_info`，匹配`Failed to create jfr datapath ctx`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建JFR，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_del_jfr_p_vjetty_info
#### 2.13 创建健康检查过程中依赖步骤失败
* 故障编号：urma_063
* 故障现象：
    * 关键日志：匹配`bondp_create_vjetty`，匹配`Failed to fill health check seg info for vjetty`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建健康检查，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_create_vjetty
#### 2.14 物理 Jetty创建时下层资源准备失败
* 故障编号：urma_064
* 故障现象：
    * 关键日志：匹配`bondp_create_pjetty`，匹配`Failed to create pjetty`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建物理 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_pjetty
#### 2.15 物理 Jetty清理阶段下层释放操作失败
* 故障编号：urma_065
* 故障现象：
    * 关键日志：匹配`bondp_delete_pjetty`，匹配`Failed to delete pjetty`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销物理 Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_pjetty
#### 2.16 执行虚拟 Jetty过程中依赖步骤失败
* 故障编号：urma_066
* 故障现象：
    * 关键日志：匹配`bondp_add_jetty_p_vjetty_id_info`，匹配`Failed to add p_vjetty_id[`，匹配`]: ret:`，匹配`, p_jetty_id:`，匹配`, v_jetty_id:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行虚拟 Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_add_jetty_p_vjetty_id_info
#### 2.17 虚拟 Jetty清理阶段下层释放操作失败
* 故障编号：urma_067
* 故障现象：
    * 关键日志：匹配`bondp_del_jetty_p_vjetty_info_without_lock`，匹配`Failed to delete p_vjetty_id node: ret:`，匹配`pjetty_id:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销虚拟 Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_del_jetty_p_vjetty_info_without_lock
#### 2.18 设备创建时下层资源准备失败
* 故障编号：urma_068
* 故障现象：
    * 关键日志：匹配`bondp_del_jetty_p_vjetty_info`，匹配`UB device must use shared jfr when create jetty.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建设备，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_del_jetty_p_vjetty_info
#### 2.19 URMA context、JFR对象、Jetty对象无效导致创建Jetty失败
* 故障编号：urma_069
* 故障现象：
    * 关键日志：匹配`bondp_del_jetty_p_vjetty_info`，匹配`Invalid well known jetty id:`，匹配`, should be in (0, 1024)`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建Jetty，调用方传入的URMA context、JFR对象、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_del_jetty_p_vjetty_info
#### 2.20 组件创建时下层资源准备失败
* 故障编号：urma_070
* 故障现象：
    * 关键日志：匹配`bondp_del_jetty_p_vjetty_info`，匹配`Failed to create bondp comp`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建组件，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_del_jetty_p_vjetty_info
#### 2.21 物理 Jetty创建时下层资源准备失败
* 故障编号：urma_071
* 故障现象：
    * 关键日志：匹配`bondp_del_jetty_p_vjetty_info`，匹配`Failed to create pjetty`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建物理 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_del_jetty_p_vjetty_info
#### 2.22 健康检查注册时下层资源准备失败
* 故障编号：urma_072
* 故障现象：
    * 关键日志：匹配`bondp_del_jetty_p_vjetty_info`，匹配`Failed to register health check seg for jetty creation`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责注册健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_del_jetty_p_vjetty_info
#### 2.23 虚拟 Jetty创建时下层资源准备失败
* 故障编号：urma_073
* 故障现象：
    * 关键日志：匹配`bondp_del_jetty_p_vjetty_info`，匹配`Failed to create vjetty,`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建虚拟 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_del_jetty_p_vjetty_info
#### 2.24 注册Jetty过程中依赖步骤失败
* 故障编号：urma_074
* 故障现象：
    * 关键日志：匹配`bondp_del_jetty_p_vjetty_info`，匹配`Failed to add jetty id to p_vjetty_id table`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于注册Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_del_jetty_p_vjetty_info
#### 2.25 Jetty创建时下层资源准备失败
* 故障编号：urma_075
* 故障现象：
    * 关键日志：匹配`bondp_del_jetty_p_vjetty_info`，匹配`Failed to create jetty ctx`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_del_jetty_p_vjetty_info
#### 2.26 Jetty清理阶段下层释放操作失败
* 故障编号：urma_076
* 故障现象：
    * 关键日志：匹配`bondp_delete_jetty`，匹配`Failed to delete jetty[`，匹配`], still in use. use_cnt:`，匹配`u`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jetty
#### 2.27 虚拟 Jetty清理阶段下层释放操作失败
* 故障编号：urma_077
* 故障现象：
    * 关键日志：匹配`bondp_delete_jetty`，匹配`Failed to delete vjetty`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销虚拟 Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jetty
#### 2.28 物理 Jetty清理阶段下层释放操作失败
* 故障编号：urma_078
* 故障现象：
    * 关键日志：匹配`bondp_delete_jetty`，匹配`Failed to delete pjetty`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销物理 Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jetty
#### 2.29 修改物理 Jetty过程中依赖步骤失败
* 故障编号：urma_079
* 故障现象：
    * 关键日志：匹配`bondp_modify_jetty`，匹配`modify pjetty fail, index:`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改物理 Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_modify_jetty
#### 2.30 物理 Jetty导入时下层资源准备失败
* 故障编号：urma_080
* 故障现象：
    * 关键日志：匹配`bondp_import_pjetty`，匹配`Failed to import tjetty`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责导入物理 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_import_pjetty
#### 2.31 Jetty相关临时结构或命令参数分配失败
* 故障编号：urma_081
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pjetty`，匹配`Failed to alloc target jetty`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：bondp_unimport_pjetty
#### 2.32 虚拟 Jetty导入时下层资源准备失败
* 故障编号：urma_082
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pjetty`，匹配`Failed to import vjetty, []:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责导入虚拟 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_unimport_pjetty
#### 2.33 Jetty导入时下层资源准备失败
* 故障编号：urma_083
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pjetty`，匹配`RM jetty import requires drv_ext.vjetty.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责导入Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_unimport_pjetty
#### 2.34 物理 Jetty导入时下层资源准备失败
* 故障编号：urma_084
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pjetty`，匹配`Failed to import pjetty`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责导入物理 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_unimport_pjetty
#### 2.35 健康检查导入时下层资源准备失败
* 故障编号：urma_085
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pjetty`，匹配`Failed to import health check seg for jetty`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责导入健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_unimport_pjetty
#### 2.36 健康检查注册时下层资源准备失败
* 故障编号：urma_086
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pjetty`，匹配`Failed to register health check task`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责注册健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_unimport_pjetty
#### 2.37 设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败
* 故障编号：urma_087
* 故障现象：
    * 关键日志：匹配`bondp_bind_jetty`，匹配`Jetty already has a binded target jetty`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：bondp_bind_jetty
#### 2.38 未找到可用于激活Jetty的有效对象或路由
* 故障编号：urma_088
* 故障现象：
    * 关键日志：匹配`bondp_bind_jetty`，匹配`No valid active slice to bind`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在激活Jetty过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位目标。
* 解决办法：无
* 函数名：bondp_bind_jetty
#### 2.39 解绑Jetty过程中依赖步骤失败
* 故障编号：urma_089
* 故障现象：
    * 关键日志：匹配`bondp_unbind_jetty`，匹配`Failed to unbind tjetty [`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解绑Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_unbind_jetty
#### 2.40 Jetty相关临时结构或命令参数分配失败
* 故障编号：urma_090
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pjfr`，匹配`Failed to alloc target jetty`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：bondp_unimport_pjfr
#### 2.41 虚拟 Jetty导入时下层资源准备失败
* 故障编号：urma_091
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pjfr`，匹配`Failed to import vjetty, []:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责导入虚拟 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_unimport_pjfr
#### 2.42 URMA context、Jetty对象无效导致获取Jetty失败
* 故障编号：urma_092
* 故障现象：
    * 关键日志：匹配`bondp_get_async_event`，匹配`failed to get invalid jetty.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_get_async_event
#### 2.43 获取组件所需输入对象无效导致获取组件失败
* 故障编号：urma_093
* 故障现象：
    * 关键日志：匹配`get_comp_urma_jetty_id`，匹配`Failed to get_comp_urma_jetty, Invalid type:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取组件，调用方传入的获取组件所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：get_comp_urma_jetty_id
#### 2.44 WR数据通路处理失败
* 故障编号：urma_094
* 故障现象：
    * 关键日志：匹配`bondp_post_send_wr_no_store`，匹配`WR->tjetty is NULL`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_post_send_wr_no_store
#### 2.45 WR数据通路处理失败
* 故障编号：urma_095
* 故障现象：
    * 关键日志：匹配`bondp_post_send_wr_and_store`，匹配`WR->tjetty is NULL`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_post_send_wr_and_store
#### 2.46 未找到可用于获取虚拟 Jetty的有效对象或路由
* 故障编号：urma_096
* 故障现象：
    * 关键日志：匹配`handle_fake_cr_with_store`，匹配`Skip fake cr because vjetty is not found, idx:`，匹配`, local_id:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在获取虚拟 Jetty过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位目标。
* 解决办法：无
* 函数名：handle_fake_cr_with_store
#### 2.47 未找到可用于获取Jetty的有效对象或路由
* 故障编号：urma_097
* 故障现象：
    * 关键日志：匹配`handle_send_cr_with_store`，匹配`Failed find jetty when handle send cr, cr.local_id:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在获取Jetty过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位目标。
* 解决办法：无
* 函数名：handle_send_cr_with_store
#### 2.48 未找到可用于获取Jetty的有效对象或路由
* 故障编号：urma_098
* 故障现象：
    * 关键日志：匹配`handle_recv_cr_with_store`，匹配`Failed to find local jetty, idx:`，匹配`, id:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在获取Jetty过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位目标。
* 解决办法：无
* 函数名：handle_recv_cr_with_store
#### 2.49 物理 Jetty数据通路处理失败
* 故障编号：urma_099
* 故障现象：
    * 关键日志：匹配`bondp_flush_jetty`，匹配`Failed to flush pjetty[`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_flush_jetty
#### 2.50 WR对象、目标Jetty对象无效导致激活WR失败
* 故障编号：urma_100
* 故障现象：
    * 关键日志：匹配`schedule_send`，匹配`Invalid wr->tjetty: NULL`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活WR，调用方传入的WR对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：schedule_send
#### 2.51 健康检查清理阶段下层释放操作失败
* 故障编号：urma_101
* 故障现象：
    * 关键日志：匹配`bondp_unregister_health_check_seg_for_jetty`，匹配`Failed to unregister health check segment`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销健康检查相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_unregister_health_check_seg_for_jetty
#### 2.52 健康检查相关临时结构或命令参数分配失败
* 故障编号：urma_102
* 故障现象：
    * 关键日志：匹配`bondp_register_health_check_seg_for_jetty`，匹配`Failed to alloc health check buffer`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配健康检查前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：bondp_register_health_check_seg_for_jetty
#### 2.53 健康检查注册时下层资源准备失败
* 故障编号：urma_103
* 故障现象：
    * 关键日志：匹配`bondp_register_health_check_seg_for_jetty`，匹配`Failed to register health check segment`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责注册健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_register_health_check_seg_for_jetty
#### 2.54 未找到可用于导入路由的有效对象或路由
* 故障编号：urma_104
* 故障现象：
    * 关键日志：匹配`import_check_tseg_by_import_result`，匹配`No valid imported route for health check seg`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在导入路由过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位目标。
* 解决办法：无
* 函数名：import_check_tseg_by_import_result
#### 2.55 Jetty对象、Segment对象无效导致导入健康检查失败
* 故障编号：urma_105
* 故障现象：
    * 关键日志：匹配`bondp_import_health_check_tseg`，匹配`Invalid rjetty for health check seg import, health check disabled`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于导入健康检查，调用方传入的Jetty对象、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_import_health_check_tseg
#### 2.56 Jetty清理阶段下层释放操作失败
* 故障编号：urma_106
* 故障现象：
    * 关键日志：匹配`bondp_relink_primary_import`，匹配`Failed to unimport old primary ptjetty, lidx:`，匹配`tidx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_relink_primary_import
#### 2.57 物理 Jetty导入时下层资源准备失败
* 故障编号：urma_107
* 故障现象：
    * 关键日志：匹配`bondp_relink_primary_import`，匹配`Failed to import recreated primary ptjetty, local_idx:`，匹配`target_idx:`，匹配`pjetty_id:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责导入物理 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_relink_primary_import
#### 2.58 未找到可用于注册健康检查的有效对象或路由
* 故障编号：urma_108
* 故障现象：
    * 关键日志：匹配`bondp_register_health_check_task`，匹配`Failed to register health task: no valid route`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在注册健康检查过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位目标。
* 解决办法：无
* 函数名：bondp_register_health_check_task
#### 2.59 物理 Jetty清理阶段下层释放操作失败
* 故障编号：urma_109
* 故障现象：
    * 关键日志：匹配`bondp_update_pjetty_id_mapping`，匹配`Failed to delete stale pjetty id mapping: , ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销物理 Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_update_pjetty_id_mapping
#### 2.60 物理 Jetty删除时下层资源准备失败
* 故障编号：urma_110
* 故障现象：
    * 关键日志：匹配`bondp_update_pjetty_id_mapping`，匹配`Failed to add recreated pjetty id mapping: , ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责删除物理 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_update_pjetty_id_mapping
#### 2.61 物理 Jetty清理阶段下层释放操作失败
* 故障编号：urma_111
* 故障现象：
    * 关键日志：匹配`bondp_rebuild_local_pjetty`，匹配`Failed to delete pjetty at idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销物理 Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_rebuild_local_pjetty
#### 2.62 物理 Jetty删除时下层资源准备失败
* 故障编号：urma_112
* 故障现象：
    * 关键日志：匹配`bondp_rebuild_local_pjetty`，匹配`Failed to recreate pjetty at idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责删除物理 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_rebuild_local_pjetty
#### 2.63 虚拟 Jetty创建时下层资源准备失败
* 故障编号：urma_113
* 故障现象：
    * 关键日志：匹配`bondp_create_vcontext`，匹配`Failed to create p_vjetty_id_table`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建虚拟 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_vcontext
#### 2.64 未找到可用于导入路由的有效对象或路由
* 故障编号：urma_114
* 故障现象：
    * 关键日志：匹配`bondp_import_pseg`，匹配`No valid direct route`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在导入路由过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位目标。
* 解决办法：无
* 函数名：bondp_import_pseg
#### 2.65 获取JFS过程中依赖步骤失败
* 故障编号：urma_115
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfs_opt`，匹配`output length too large, out.len=`，匹配`, buf.len=`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_get_jfs_opt
#### 2.66 获取JFC过程中依赖步骤失败
* 故障编号：urma_116
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfc_opt`，匹配`output length too large, out.len=`，匹配`, buf.len=`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_get_jfc_opt
#### 2.67 URMA context无效导致导入JFR失败
* 故障编号：urma_117
* 故障现象：
    * 关键日志：匹配`urma_cmd_import_jfr`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于导入JFR，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_import_jfr
#### 2.68 URMA context无效导致导入JFR失败
* 故障编号：urma_118
* 故障现象：
    * 关键日志：匹配`urma_cmd_import_jfr_ex`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于导入JFR，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_import_jfr_ex
#### 2.69 URMA context无效导致解除导入JFR失败
* 故障编号：urma_119
* 故障现象：
    * 关键日志：匹配`urma_cmd_unimport_jfr`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入JFR，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_unimport_jfr
#### 2.70 URMA context、JFS对象、Jetty对象、目标Jetty对象无效导致执行Jetty失败
* 故障编号：urma_120
* 故障现象：
    * 关键日志：匹配`urma_cmd_advise_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行Jetty，调用方传入的URMA context、JFS对象、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_advise_jetty
#### 2.71 获取JFR过程中依赖步骤失败
* 故障编号：urma_121
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfr_opt`，匹配`output length too large, out.len=`，匹配`, buf.len=`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_get_jfr_opt
#### 2.72 URMA context、JFR对象、Jetty对象、目标Jetty对象无效导致去激活Jetty失败
* 故障编号：urma_122
* 故障现象：
    * 关键日志：匹配`urma_cmd_unadvise_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活Jetty，调用方传入的URMA context、JFR对象、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_unadvise_jetty
#### 2.73 URMA context、Jetty对象、目标Jetty对象无效导致绑定Jetty失败
* 故障编号：urma_123
* 故障现象：
    * 关键日志：匹配`urma_cmd_bind_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，调用方传入的URMA context、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_bind_jetty
#### 2.74 URMA context、Jetty对象、目标Jetty对象无效导致绑定Jetty失败
* 故障编号：urma_124
* 故障现象：
    * 关键日志：匹配`urma_cmd_bind_jetty_ex`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，调用方传入的URMA context、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_bind_jetty_ex
#### 2.75 URMA context、Jetty对象、目标Jetty对象无效导致解绑Jetty失败
* 故障编号：urma_125
* 故障现象：
    * 关键日志：匹配`urma_cmd_unbind_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解绑Jetty，调用方传入的URMA context、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_unbind_jetty
#### 2.76 URMA context、Jetty对象无效导致创建Jetty失败
* 故障编号：urma_126
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_create_jetty
#### 2.77 创建Jetty过程中依赖步骤失败
* 故障编号：urma_127
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_jetty`，匹配`failed to fill jetty cfg`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_create_jetty
#### 2.78 URMA context、Jetty对象无效导致修改Jetty失败
* 故障编号：urma_128
* 故障现象：
    * 关键日志：匹配`urma_cmd_modify_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_modify_jetty
#### 2.79 URMA context、Jetty对象无效导致查询Jetty失败
* 故障编号：urma_129
* 故障现象：
    * 关键日志：匹配`urma_cmd_query_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_query_jetty
#### 2.80 Jetty对象无效导致查询Jetty失败
* 故障编号：urma_130
* 故障现象：
    * 关键日志：匹配`urma_cmd_query_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询Jetty，调用方传入的Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_query_jetty
#### 2.81 URMA context、Jetty对象无效导致删除Jetty失败
* 故障编号：urma_131
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jetty
#### 2.82 删除ioctl的ioctl调用返回失败
* 故障编号：urma_132
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jetty`，匹配`ioctl failed, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交删除ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_delete_jetty
#### 2.83 Jetty对象无效导致删除Jetty失败
* 故障编号：urma_133
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jetty_batch`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jetty_batch
#### 2.84 URMA context、Jetty对象无效导致删除Jetty失败
* 故障编号：urma_134
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jetty_batch`，匹配`Invalid parameter, index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jetty_batch
#### 2.85 URMA context、Jetty对象无效导致删除Jetty失败
* 故障编号：urma_135
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jetty_batch`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jetty_batch
#### 2.86 Jetty清理阶段下层释放操作失败
* 故障编号：urma_136
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jetty_batch`，匹配`jetty not from the same dev, cannot delete in a batch, index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_cmd_delete_jetty_batch
#### 2.87 Jetty相关临时结构或命令参数分配失败
* 故障编号：urma_137
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jetty_batch`，匹配`Failed to malloc buffer.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在删除Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_cmd_delete_jetty_batch
#### 2.88 删除ioctl的ioctl调用返回失败
* 故障编号：urma_138
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jetty_batch`，匹配`ioctl failed in urma_cmd_delete_jetty_batch , ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交删除ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_delete_jetty_batch
#### 2.89 删除Jetty过程中依赖步骤失败
* 故障编号：urma_139
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jetty_batch`，匹配`bad jetty index exceed array length, bad_jetty_index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_delete_jetty_batch
#### 2.90 URMA context、目标Jetty对象无效导致导入Jetty失败
* 故障编号：urma_140
* 故障现象：
    * 关键日志：匹配`urma_cmd_import_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于导入Jetty，调用方传入的URMA context、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_import_jetty
#### 2.91 URMA context、目标Jetty对象无效导致导入Jetty失败
* 故障编号：urma_141
* 故障现象：
    * 关键日志：匹配`urma_cmd_import_jetty_ex`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于导入Jetty，调用方传入的URMA context、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_import_jetty_ex
#### 2.92 URMA context、目标Jetty对象无效导致解除导入Jetty失败
* 故障编号：urma_142
* 故障现象：
    * 关键日志：匹配`urma_cmd_unimport_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入Jetty，调用方传入的URMA context、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_unimport_jetty
#### 2.93 URMA context、目标Jetty对象无效导致创建Jetty失败
* 故障编号：urma_143
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_jetty_grp`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建Jetty，调用方传入的URMA context、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_create_jetty_grp
#### 2.94 URMA context无效导致删除Jetty失败
* 故障编号：urma_144
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jetty_grp`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jetty_grp
#### 2.95 URMA context、Jetty对象无效导致分配Jetty失败
* 故障编号：urma_145
* 故障现象：
    * 关键日志：匹配`urma_cmd_alloc_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_alloc_jetty
#### 2.96 分配Jetty过程中依赖步骤失败
* 故障编号：urma_146
* 故障现象：
    * 关键日志：匹配`urma_cmd_alloc_jetty`，匹配`failed to fill jetty cfg`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_alloc_jetty
#### 2.97 URMA context、Jetty对象无效导致释放Jetty失败
* 故障编号：urma_147
* 故障现象：
    * 关键日志：匹配`urma_cmd_free_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_free_jetty
#### 2.98 释放ioctl的ioctl调用返回失败
* 故障编号：urma_148
* 故障现象：
    * 关键日志：匹配`urma_cmd_free_jetty`，匹配`ioctl failed, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交释放ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_free_jetty
#### 2.99 URMA context、Jetty对象无效导致设置Jetty失败
* 故障编号：urma_149
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jetty_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_set_jetty_opt
#### 2.100 URMA context、Jetty对象无效导致设置Jetty失败
* 故障编号：urma_150
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jetty_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_set_jetty_opt
#### 2.101 设置Jetty过程中依赖步骤失败
* 故障编号：urma_151
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jetty_opt`，匹配`jetty->jetty_cfg.shared.jfc is not exist`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_set_jetty_opt
#### 2.102 设置Jetty过程中依赖步骤失败
* 故障编号：urma_152
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jetty_opt`，匹配`jetty->jetty_cfg.shared.jfr is not exist`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_set_jetty_opt
#### 2.103 设置Jetty过程中依赖步骤失败
* 故障编号：urma_153
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jetty_opt`，匹配`jetty->jetty_cfg.jetty_grp is not exist`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_set_jetty_opt
#### 2.104 设置Jetty过程中依赖步骤失败
* 故障编号：urma_154
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jetty_opt`，匹配`jetty->jetty_cfg.jfs_cfg.jfc is not exist`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_set_jetty_opt
#### 2.105 设置ioctl的ioctl调用返回失败
* 故障编号：urma_155
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jetty_opt`，匹配`ioctl failed in urma_cmd_set_jetty_opt, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交设置ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_set_jetty_opt
#### 2.106 URMA context、Jetty对象无效导致获取Jetty失败
* 故障编号：urma_156
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jetty_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_jetty_opt
#### 2.107 URMA context、Jetty对象无效导致获取Jetty失败
* 故障编号：urma_157
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jetty_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_jetty_opt
#### 2.108 获取ioctl的ioctl调用返回失败
* 故障编号：urma_158
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jetty_opt`，匹配`ioctl failed in urma_cmd_get_jetty_opt, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交获取ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_get_jetty_opt
#### 2.109 URMA context无效导致获取Jetty失败
* 故障编号：urma_159
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jetty_opt`，匹配`Invalid out buffer from kernel.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取Jetty，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_jetty_opt
#### 2.110 URMA context、Jetty对象无效导致激活Jetty失败
* 故障编号：urma_160
* 故障现象：
    * 关键日志：匹配`urma_cmd_active_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_active_jetty
#### 2.111 JFR对象、Jetty对象无效导致激活Jetty失败
* 故障编号：urma_161
* 故障现象：
    * 关键日志：匹配`urma_cmd_active_jetty`，匹配`Invalid flag.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活Jetty，调用方传入的JFR对象、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_active_jetty
#### 2.112 激活ioctl的ioctl调用返回失败
* 故障编号：urma_162
* 故障现象：
    * 关键日志：匹配`urma_cmd_active_jetty`，匹配`ioctl failed in urma_cmd_active_jetty, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交激活ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_active_jetty
#### 2.113 URMA context、Jetty对象无效导致去激活Jetty失败
* 故障编号：urma_163
* 故障现象：
    * 关键日志：匹配`urma_cmd_deactive_jetty`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_deactive_jetty
#### 2.114 去激活ioctl的ioctl调用返回失败
* 故障编号：urma_164
* 故障现象：
    * 关键日志：匹配`urma_cmd_deactive_jetty`，匹配`ioctl failed in urma_cmd_deactive_jetty, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交去激活ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_deactive_jetty
#### 2.115 URMA context无效导致修改TP失败
* 故障编号：urma_165
* 故障现象：
    * 关键日志：匹配`urma_cmd_modify_tp`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改TP，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_modify_tp
#### 2.116 URMA context、sysfs设备信息、目标Jetty对象无效导致导入Jetty失败
* 故障编号：urma_166
* 故障现象：
    * 关键日志：匹配`urma_cmd_import_jetty_async`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于导入Jetty，调用方传入的URMA context、sysfs设备信息、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_import_jetty_async
#### 2.117 URMA context、目标Jetty对象无效导致解除导入Jetty失败
* 故障编号：urma_167
* 故障现象：
    * 关键日志：匹配`urma_cmd_unimport_jetty_async`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入Jetty，调用方传入的URMA context、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_unimport_jetty_async
#### 2.118 URMA context、Jetty对象、目标Jetty对象无效导致绑定Jetty失败
* 故障编号：urma_168
* 故障现象：
    * 关键日志：匹配`urma_cmd_bind_jetty_async`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，调用方传入的URMA context、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_bind_jetty_async
#### 2.119 URMA context、Jetty对象、目标Jetty对象无效导致解绑Jetty失败
* 故障编号：urma_169
* 故障现象：
    * 关键日志：匹配`urma_cmd_unbind_jetty_async`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解绑Jetty，调用方传入的URMA context、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_unbind_jetty_async
#### 2.120 URMA context、Jetty对象无效导致获取TP失败
* 故障编号：urma_170
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_tp_list`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取TP，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_tp_list
#### 2.121 URMA context无效导致设置TP失败
* 故障编号：urma_171
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_tp_attr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置TP，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_set_tp_attr
#### 2.122 URMA context无效导致设置TP失败
* 故障编号：urma_172
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_tp_attr`，匹配`Invalid tp_attr bytes.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置TP，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_set_tp_attr
#### 2.123 设置ioctl的ioctl调用返回失败
* 故障编号：urma_173
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_tp_attr`，匹配`Failed in ioctl set_tp_attr, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交设置ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_set_tp_attr
#### 2.124 URMA context无效导致获取TP失败
* 故障编号：urma_174
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_tp_attr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取TP，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_tp_attr
#### 2.125 URMA context无效导致获取TP失败
* 故障编号：urma_175
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_tp_attr`，匹配`Invalid tp_attr bytes.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取TP，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_tp_attr
#### 2.126 获取ioctl的ioctl调用返回失败
* 故障编号：urma_176
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_tp_attr`，匹配`Failed in ioctl get_tp_attr, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交获取ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_get_tp_attr
#### 2.127 URMA context无效导致获取TP失败
* 故障编号：urma_177
* 故障现象：
    * 关键日志：匹配`urma_cmd_exchange_tp_info`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取TP，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_exchange_tp_info
#### 2.128 URMA context、provider操作表无效导致解除导入JFR失败
* 故障编号：urma_178
* 故障现象：
    * 关键日志：匹配`urma_unimport_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入JFR，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unimport_jfr
#### 2.129 URMA context、provider操作表、provider未提供unimport_jfr操作实现无效导致解除导入JFR失败
* 故障编号：urma_179
* 故障现象：
    * 关键日志：匹配`urma_unimport_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入JFR，调用方传入的URMA context、provider操作表、provider未提供unimport_jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unimport_jfr
#### 2.130 URMA context、设备对象、JFR对象无效导致创建Jetty失败
* 故障编号：urma_180
* 故障现象：
    * 关键日志：匹配`urma_create_jetty_check_trans_mode`，匹配`Invalid parameter, trans_mode:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建Jetty，调用方传入的URMA context、设备对象、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_create_jetty_check_trans_mode
#### 2.131 创建设备过程中依赖步骤失败
* 故障编号：urma_181
* 故障现象：
    * 关键日志：匹配`urma_create_jetty_check_trans_mode`，匹配`UB dev should use share jfr!`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_create_jetty_check_trans_mode
#### 2.132 URMA context、设备对象、JFR对象无效导致创建Jetty失败
* 故障编号：urma_182
* 故障现象：
    * 关键日志：匹配`urma_create_jetty_check_trans_mode`，匹配`Invalid parameter, trans_mode:`，匹配`, order_type:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建Jetty，调用方传入的URMA context、设备对象、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_create_jetty_check_trans_mode
#### 2.133 JFR对象无效导致创建JFR失败
* 故障编号：urma_183
* 故障现象：
    * 关键日志：匹配`urma_create_jetty_check_trans_mode`，匹配`jfr cfg is null or trans_mode or order_type invalid with non shared jfr flag.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFR，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_create_jetty_check_trans_mode
#### 2.134 JFR对象无效导致创建JFR失败
* 故障编号：urma_184
* 故障现象：
    * 关键日志：匹配`urma_create_jetty_check_trans_mode`，匹配`jfr is null or trans_mode or order_type invalid with shared jfr flag.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFR，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_create_jetty_check_trans_mode
#### 2.135 创建Jetty过程中依赖步骤失败
* 故障编号：urma_185
* 故障现象：
    * 关键日志：匹配`urma_create_jetty_check_dev_cap`，匹配`jetty_grp jetty cnt:`，匹配`, max_jetty in grp:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_create_jetty_check_dev_cap
#### 2.136 创建Jetty过程中依赖步骤失败
* 故障编号：urma_186
* 故障现象：
    * 关键日志：匹配`urma_create_jetty_check_dev_cap`，匹配`jetty cfg out of range, jfs_depth:`，匹配`, max_jfs_depth:`，匹配`, inline_data:`，匹配`, max_jfs_inline_len:`，匹配`, jfr_depth:`，匹配`, max_jfr_depth:`，匹配`, jfs_sge:`，匹配`hu, max_jfs_sge:`，匹配`, jfs_rsge:`，匹配`hu, max_jfs_rsge:`，匹配`, jfr_sge:`，匹配`hu, max_jfr_sge:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_create_jetty_check_dev_cap
#### 2.137 JFR对象无效导致执行Token失败
* 故障编号：urma_187
* 故障现象：
    * 关键日志：匹配`urma_check_jetty_cfg_with_jetty_grp`，匹配`Invalid token with share_jfr.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行Token，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_jetty_cfg_with_jetty_grp
#### 2.138 JFR对象无效导致执行Token失败
* 故障编号：urma_188
* 故障现象：
    * 关键日志：匹配`urma_check_jetty_cfg_with_jetty_grp`，匹配`Invalid token with unshared jfr.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行Token，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_jetty_cfg_with_jetty_grp
#### 2.139 删除Jetty过程中依赖步骤失败
* 故障编号：urma_189
* 故障现象：
    * 关键日志：匹配`urma_add_jetty_to_jetty_grp`，匹配`failed to add jetty to jetty_grp.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_add_jetty_to_jetty_grp
#### 2.140 Jetty清理阶段下层释放操作失败
* 故障编号：urma_190
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_to_jetty_grp`，匹配`failed to delete jetty to jetty_grp.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_jetty_to_jetty_grp
#### 2.141 Jetty对象无效导致创建JFC失败
* 故障编号：urma_191
* 故障现象：
    * 关键日志：匹配`urma_create_jetty_check_jfc`，匹配`Invalid parameter, jfc is NULL in jfs_cfg.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFC，调用方传入的Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_create_jetty_check_jfc
#### 2.142 JFR对象无效导致创建JFR失败
* 故障编号：urma_192
* 故障现象：
    * 关键日志：匹配`urma_create_jetty_check_jfc`，匹配`Invalid parameter, jfr cfg is null or jfc is NULL with non shared jfr flag.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFR，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_create_jetty_check_jfc
#### 2.143 JFR对象无效导致创建JFR失败
* 故障编号：urma_193
* 故障现象：
    * 关键日志：匹配`urma_create_jetty_check_jfc`，匹配`Invalid parameter, jfr is null or jfc is NULL with shared jfr flag.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFR，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_create_jetty_check_jfc
#### 2.144 URMA context、设备对象、JFR对象无效导致创建Jetty失败
* 故障编号：urma_194
* 故障现象：
    * 关键日志：匹配`urma_create_jetty_check_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建Jetty，调用方传入的URMA context、设备对象、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_create_jetty_check_jfc
#### 2.145 URMA context、provider操作表、provider未提供create_jetty操作实现无效导致创建Jetty失败
* 故障编号：urma_195
* 故障现象：
    * 关键日志：匹配`urma_create_jetty_check_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建Jetty，调用方传入的URMA context、provider操作表、provider未提供create_jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_create_jetty_check_jfc
#### 2.146 Jetty创建时下层资源准备失败
* 故障编号：urma_196
* 故障现象：
    * 关键日志：匹配`urma_create_jetty_check_jfc`，匹配`[DRV_ERR]create_jetty failed, dev_name:`，匹配`, eid_idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：urma_create_jetty_check_jfc
#### 2.147 URMA context、Jetty对象无效导致修改Jetty失败
* 故障编号：urma_197
* 故障现象：
    * 关键日志：匹配`urma_modify_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_modify_jetty
#### 2.148 URMA context、provider操作表、Jetty对象、provider未提供modify_jetty操作实现无效导致修改Jetty失败
* 故障编号：urma_198
* 故障现象：
    * 关键日志：匹配`urma_modify_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改Jetty，调用方传入的URMA context、provider操作表、Jetty对象、provider未提供modify_jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_modify_jetty
#### 2.149 URMA context、provider操作表、Jetty对象无效导致查询Jetty失败
* 故障编号：urma_199
* 故障现象：
    * 关键日志：匹配`urma_query_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询Jetty，调用方传入的URMA context、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_query_jetty
#### 2.150 URMA context、provider操作表、Jetty对象、provider未提供query_jetty操作实现无效导致查询Jetty失败
* 故障编号：urma_200
* 故障现象：
    * 关键日志：匹配`urma_query_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询Jetty，调用方传入的URMA context、provider操作表、Jetty对象、provider未提供query_jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_query_jetty
#### 2.151 URMA context、provider操作表、Jetty对象无效导致释放Jetty失败
* 故障编号：urma_201
* 故障现象：
    * 关键日志：匹配`urma_free_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放Jetty，调用方传入的URMA context、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_free_jetty
#### 2.152 释放Jetty过程中依赖步骤失败
* 故障编号：urma_202
* 故障现象：
    * 关键日志：匹配`urma_free_jetty`，匹配`jetty still actived, please deactived first`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_free_jetty
#### 2.153 Jetty清理阶段下层释放操作失败
* 故障编号：urma_203
* 故障现象：
    * 关键日志：匹配`urma_free_jetty`，匹配`Failed to delete jetty because it has remote jetty, try unbind first`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_free_jetty
#### 2.154 URMA context、provider操作表、Jetty对象、provider未提供free_jetty操作实现无效导致释放Jetty失败
* 故障编号：urma_204
* 故障现象：
    * 关键日志：匹配`urma_free_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放Jetty，调用方传入的URMA context、provider操作表、Jetty对象、provider未提供free_jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_free_jetty
#### 2.155 URMA context、provider操作表、Jetty对象无效导致删除Jetty失败
* 故障编号：urma_205
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的URMA context、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jetty
#### 2.156 Jetty清理阶段下层释放操作失败
* 故障编号：urma_206
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty`，匹配`jetty still deactived, can not delete.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_jetty
#### 2.157 Jetty清理阶段下层释放操作失败
* 故障编号：urma_207
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty`，匹配`Failed to delete jetty because it has remote jetty, try unbind first`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_jetty
#### 2.158 URMA context、provider操作表、Jetty对象、provider未提供delete_jetty操作实现无效导致删除Jetty失败
* 故障编号：urma_208
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的URMA context、provider操作表、Jetty对象、provider未提供delete_jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jetty
#### 2.159 Jetty清理阶段下层释放操作失败
* 故障编号：urma_209
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty`，匹配`[DRV_ERR]Failed to delete jetty, dev_name:`，匹配`, eid_idx:`，匹配`, id:`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_jetty
#### 2.160 URMA context、provider操作表、Jetty对象无效导致删除Jetty失败
* 故障编号：urma_210
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_batch`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的URMA context、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jetty_batch
#### 2.161 Jetty相关临时结构或命令参数分配失败
* 故障编号：urma_211
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_batch`，匹配`Failed to alloc memory.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_delete_jetty_batch
#### 2.162 Jetty对象无效导致删除Jetty失败
* 故障编号：urma_212
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_batch`，匹配`Invalid parameter, index`，匹配`jetty in the array is NULL.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jetty_batch
#### 2.163 Jetty清理阶段下层释放操作失败
* 故障编号：urma_213
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_batch`，匹配`Failed to delete as jetty has remote jetty, try unbind, index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_jetty_batch
#### 2.164 URMA context、设备对象、sysfs设备信息、provider操作表、Jetty对象无效导致删除Jetty失败
* 故障编号：urma_214
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_batch`，匹配`Invalid parameter, index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jetty_batch
#### 2.165 Jetty清理阶段下层释放操作失败
* 故障编号：urma_215
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_batch`，匹配`Failed to delete jetty batch, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_jetty_batch
#### 2.166 URMA context、Jetty对象无效导致刷出Jetty失败
* 故障编号：urma_216
* 故障现象：
    * 关键日志：匹配`urma_flush_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于刷出Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_flush_jetty
#### 2.167 URMA context、provider操作表、Jetty对象、provider未提供flush_jetty操作实现无效导致刷出Jetty失败
* 故障编号：urma_217
* 故障现象：
    * 关键日志：匹配`urma_flush_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于刷出Jetty，调用方传入的URMA context、provider操作表、Jetty对象、provider未提供flush_jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_flush_jetty
#### 2.168 URMA context、provider操作表、目标Jetty对象、provider未提供import_jetty_ex操作实现无效导致刷出Jetty失败
* 故障编号：urma_218
* 故障现象：
    * 关键日志：匹配`urma_flush_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于刷出Jetty，调用方传入的URMA context、provider操作表、目标Jetty对象、provider未提供import_jetty_ex操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_flush_jetty
#### 2.169 URMA context、设备对象、sysfs设备信息、provider操作表、目标Jetty对象无效导致刷出Jetty失败
* 故障编号：urma_219
* 故障现象：
    * 关键日志：匹配`urma_flush_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于刷出Jetty，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_flush_jetty
#### 2.170 URMA context、设备对象、sysfs设备信息、provider操作表无效导致刷出Jetty失败
* 故障编号：urma_220
* 故障现象：
    * 关键日志：匹配`urma_flush_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于刷出Jetty，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_flush_jetty
#### 2.171 URMA context、provider操作表无效导致刷出Jetty失败
* 故障编号：urma_221
* 故障现象：
    * 关键日志：匹配`urma_flush_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于刷出Jetty，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_flush_jetty
#### 2.172 URMA context、provider操作表、目标Jetty对象无效导致刷出Jetty失败
* 故障编号：urma_222
* 故障现象：
    * 关键日志：匹配`urma_flush_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于刷出Jetty，调用方传入的URMA context、provider操作表、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_flush_jetty
#### 2.173 URMA context、provider操作表、目标Jetty对象、provider未提供import_jetty_ex操作实现无效导致刷出Jetty失败
* 故障编号：urma_223
* 故障现象：
    * 关键日志：匹配`urma_flush_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于刷出Jetty，调用方传入的URMA context、provider操作表、目标Jetty对象、provider未提供import_jetty_ex操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_flush_jetty
#### 2.174 URMA context、provider操作表、目标Jetty对象无效导致解除导入Jetty失败
* 故障编号：urma_224
* 故障现象：
    * 关键日志：匹配`urma_unimport_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入Jetty，调用方传入的URMA context、provider操作表、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unimport_jetty
#### 2.175 URMA context、provider操作表、目标Jetty对象、provider未提供unimport_jetty操作实现无效导致解除导入Jetty失败
* 故障编号：urma_225
* 故障现象：
    * 关键日志：匹配`urma_unimport_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入Jetty，调用方传入的URMA context、provider操作表、目标Jetty对象、provider未提供unimport_jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unimport_jetty
#### 2.176 URMA context、provider操作表、Jetty对象、目标Jetty对象无效导致绑定Jetty失败
* 故障编号：urma_226
* 故障现象：
    * 关键日志：匹配`urma_bind_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，调用方传入的URMA context、provider操作表、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_bind_jetty
#### 2.177 URMA context、设备对象、sysfs设备信息、provider操作表、Jetty对象、目标Jetty对象无效导致绑定Jetty失败
* 故障编号：urma_227
* 故障现象：
    * 关键日志：匹配`urma_bind_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_bind_jetty
#### 2.178 绑定Jetty过程中依赖步骤失败
* 故障编号：urma_228
* 故障现象：
    * 关键日志：匹配`urma_bind_jetty`，匹配`Not allowed to bind local jetty:`，匹配`of mode:`，匹配`with remote jetty:`，匹配`of mode:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_bind_jetty
#### 2.179 绑定Jetty过程中依赖步骤失败
* 故障编号：urma_229
* 故障现象：
    * 关键日志：匹配`urma_bind_jetty`，匹配`Not allowed to bind local jetty:`，匹配`, with remote jetty:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_bind_jetty
#### 2.180 URMA context、provider操作表、Jetty对象、目标Jetty对象无效导致绑定Jetty失败
* 故障编号：urma_230
* 故障现象：
    * 关键日志：匹配`urma_bind_jetty_ex`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，调用方传入的URMA context、provider操作表、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_bind_jetty_ex
#### 2.181 绑定Jetty过程中依赖步骤失败
* 故障编号：urma_231
* 故障现象：
    * 关键日志：匹配`urma_bind_jetty_ex`，匹配`Not allowed to bind local jetty:`，匹配`of mode:`，匹配`with remote jetty:`，匹配`of mode:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_bind_jetty_ex
#### 2.182 绑定Jetty过程中依赖步骤失败
* 故障编号：urma_232
* 故障现象：
    * 关键日志：匹配`urma_bind_jetty_ex`，匹配`Not allowed to bind local jetty:`，匹配`, with remote jetty:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_bind_jetty_ex
#### 2.183 URMA context、provider操作表、Jetty对象、目标Jetty对象、provider未提供bind_jetty_ex操作实现无效导致绑定Jetty失败
* 故障编号：urma_233
* 故障现象：
    * 关键日志：匹配`urma_bind_jetty_ex`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，调用方传入的URMA context、provider操作表、Jetty对象、目标Jetty对象、provider未提供bind_jetty_ex操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_bind_jetty_ex
#### 2.184 URMA context、provider操作表、Jetty对象、目标Jetty对象无效导致解绑Jetty失败
* 故障编号：urma_234
* 故障现象：
    * 关键日志：匹配`urma_unbind_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解绑Jetty，调用方传入的URMA context、provider操作表、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unbind_jetty
#### 2.185 解绑TP过程中依赖步骤失败
* 故障编号：urma_235
* 故障现象：
    * 关键日志：匹配`urma_unbind_jetty`，匹配`Not allowed to call unbind as the tp mode of jetty :`，匹配`is:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解绑TP，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_unbind_jetty
#### 2.186 URMA context、provider操作表、Jetty对象、provider未提供unbind_jetty操作实现无效导致解绑Jetty失败
* 故障编号：urma_236
* 故障现象：
    * 关键日志：匹配`urma_unbind_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解绑Jetty，调用方传入的URMA context、provider操作表、Jetty对象、provider未提供unbind_jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unbind_jetty
#### 2.187 URMA context、provider操作表、Jetty对象、目标Jetty对象无效导致解绑Jetty失败
* 故障编号：urma_237
* 故障现象：
    * 关键日志：匹配`urma_advise_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解绑Jetty，调用方传入的URMA context、provider操作表、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_advise_jetty
#### 2.188 URMA context、设备对象、Jetty对象、目标Jetty对象无效导致执行Jetty失败
* 故障编号：urma_238
* 故障现象：
    * 关键日志：匹配`urma_advise_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行Jetty，调用方传入的URMA context、设备对象、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_advise_jetty
#### 2.189 URMA context、设备对象、provider操作表、Jetty对象、目标Jetty对象无效导致执行Jetty失败
* 故障编号：urma_239
* 故障现象：
    * 关键日志：匹配`urma_advise_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行Jetty，调用方传入的URMA context、设备对象、provider操作表、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_advise_jetty
#### 2.190 URMA context、provider操作表、Jetty对象、目标Jetty对象无效导致执行Jetty失败
* 故障编号：urma_240
* 故障现象：
    * 关键日志：匹配`urma_unadvise_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行Jetty，调用方传入的URMA context、provider操作表、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unadvise_jetty
#### 2.191 URMA context、设备对象、Jetty对象、目标Jetty对象无效导致执行Jetty失败
* 故障编号：urma_241
* 故障现象：
    * 关键日志：匹配`urma_unadvise_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行Jetty，调用方传入的URMA context、设备对象、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unadvise_jetty
#### 2.192 URMA context、设备对象、provider操作表、Jetty对象、目标Jetty对象无效导致执行Jetty失败
* 故障编号：urma_242
* 故障现象：
    * 关键日志：匹配`urma_unadvise_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行Jetty，调用方传入的URMA context、设备对象、provider操作表、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unadvise_jetty
#### 2.193 URMA context、provider操作表、Jetty对象、目标Jetty对象无效导致导入Jetty失败
* 故障编号：urma_243
* 故障现象：
    * 关键日志：匹配`urma_unadvise_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于导入Jetty，调用方传入的URMA context、provider操作表、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unadvise_jetty
#### 2.194 URMA context、provider操作表、provider未提供import_jetty_async操作实现无效导致导入Jetty失败
* 故障编号：urma_244
* 故障现象：
    * 关键日志：匹配`urma_unadvise_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于导入Jetty，调用方传入的URMA context、provider操作表、provider未提供import_jetty_async操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unadvise_jetty
#### 2.195 Jetty相关临时结构或命令参数分配失败
* 故障编号：urma_245
* 故障现象：
    * 关键日志：匹配`urma_unadvise_jetty`，匹配`Failed to alloc incomplete_tjetty.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_unadvise_jetty
#### 2.196 URMA context、目标Jetty对象无效导致解除导入Jetty失败
* 故障编号：urma_246
* 故障现象：
    * 关键日志：匹配`urma_unimport_jetty_async`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入Jetty，调用方传入的URMA context、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unimport_jetty_async
#### 2.197 URMA context、provider操作表、Jetty对象、目标Jetty对象、provider未提供unimport_jetty_async操作实现无效导致解除导入Jetty失败
* 故障编号：urma_247
* 故障现象：
    * 关键日志：匹配`urma_unimport_jetty_async`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入Jetty，调用方传入的URMA context、provider操作表、Jetty对象、目标Jetty对象、provider未提供unimport_jetty_async操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unimport_jetty_async
#### 2.198 Jetty清理阶段下层释放操作失败
* 故障编号：urma_248
* 故障现象：
    * 关键日志：匹配`urma_unimport_jetty_async`，匹配`Failed to unimport jetty.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_unimport_jetty_async
#### 2.199 URMA context、Jetty对象、目标Jetty对象无效导致绑定Jetty失败
* 故障编号：urma_249
* 故障现象：
    * 关键日志：匹配`urma_bind_jetty_async`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，调用方传入的URMA context、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_bind_jetty_async
#### 2.200 绑定Jetty过程中依赖步骤失败
* 故障编号：urma_250
* 故障现象：
    * 关键日志：匹配`urma_bind_jetty_async`，匹配`Not allowed to bind local jetty:`，匹配`of mode:`，匹配`with remote jetty:`，匹配`of mode:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_bind_jetty_async
#### 2.201 绑定Jetty过程中依赖步骤失败
* 故障编号：urma_251
* 故障现象：
    * 关键日志：匹配`urma_bind_jetty_async`，匹配`Not allowed to bind local jetty:`，匹配`, with remote jetty:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_bind_jetty_async
#### 2.202 URMA context、provider操作表、Jetty对象、目标Jetty对象、provider未提供bind_jetty_async操作实现无效导致绑定Jetty失败
* 故障编号：urma_252
* 故障现象：
    * 关键日志：匹配`urma_bind_jetty_async`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于绑定Jetty，调用方传入的URMA context、provider操作表、Jetty对象、目标Jetty对象、provider未提供bind_jetty_async操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_bind_jetty_async
#### 2.203 URMA context、provider操作表、Jetty对象、目标Jetty对象无效导致解绑Jetty失败
* 故障编号：urma_253
* 故障现象：
    * 关键日志：匹配`urma_unbind_jetty_async`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解绑Jetty，调用方传入的URMA context、provider操作表、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unbind_jetty_async
#### 2.204 解绑TP过程中依赖步骤失败
* 故障编号：urma_254
* 故障现象：
    * 关键日志：匹配`urma_unbind_jetty_async`，匹配`Not allowed to call unbind as the tp mode of jetty :`，匹配`is:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解绑TP，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_unbind_jetty_async
#### 2.205 URMA context、provider操作表、Jetty对象、provider未提供unbind_jetty_async操作实现无效导致解绑Jetty失败
* 故障编号：urma_255
* 故障现象：
    * 关键日志：匹配`urma_unbind_jetty_async`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解绑Jetty，调用方传入的URMA context、provider操作表、Jetty对象、provider未提供unbind_jetty_async操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unbind_jetty_async
#### 2.206 URMA context、设备对象、provider操作表、Jetty对象无效导致分配Jetty失败
* 故障编号：urma_256
* 故障现象：
    * 关键日志：匹配`urma_alloc_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配Jetty，调用方传入的URMA context、设备对象、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_alloc_jetty
#### 2.207 URMA context、设备对象、provider操作表、Jetty对象无效导致分配Jetty失败
* 故障编号：urma_257
* 故障现象：
    * 关键日志：匹配`urma_alloc_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配Jetty，调用方传入的URMA context、设备对象、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_alloc_jetty
#### 2.208 URMA context、设备对象、Jetty对象无效导致分配Jetty失败
* 故障编号：urma_258
* 故障现象：
    * 关键日志：匹配`urma_alloc_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配Jetty，调用方传入的URMA context、设备对象、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_alloc_jetty
#### 2.209 URMA context、provider操作表无效导致分配Jetty失败
* 故障编号：urma_259
* 故障现象：
    * 关键日志：匹配`urma_alloc_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配Jetty，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_alloc_jetty
#### 2.210 URMA context、provider操作表、provider未提供alloc_jetty操作实现无效导致分配Jetty失败
* 故障编号：urma_260
* 故障现象：
    * 关键日志：匹配`urma_alloc_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配Jetty，调用方传入的URMA context、provider操作表、provider未提供alloc_jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_alloc_jetty
#### 2.211 Jetty相关临时结构或命令参数分配失败
* 故障编号：urma_261
* 故障现象：
    * 关键日志：匹配`urma_alloc_jetty`，匹配`alloc_jetty failed.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_alloc_jetty
#### 2.212 URMA context、Jetty对象无效导致设置Jetty失败
* 故障编号：urma_262
* 故障现象：
    * 关键日志：匹配`urma_set_jetty_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_jetty_opt
#### 2.213 设置Jetty过程中依赖步骤失败
* 故障编号：urma_263
* 故障现象：
    * 关键日志：匹配`urma_set_jetty_opt`，匹配`Failed to set opt, jetty has been activated`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_jetty_opt
#### 2.214 provider操作表、Jetty对象无效导致设置Jetty失败
* 故障编号：urma_264
* 故障现象：
    * 关键日志：匹配`urma_set_jetty_opt`，匹配`invalid opt id or opt len`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Jetty，调用方传入的provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_jetty_opt
#### 2.215 URMA context、provider操作表、Jetty对象、provider未提供set_jetty_opt操作实现无效导致设置Jetty失败
* 故障编号：urma_265
* 故障现象：
    * 关键日志：匹配`urma_set_jetty_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Jetty，调用方传入的URMA context、provider操作表、Jetty对象、provider未提供set_jetty_opt操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_jetty_opt
#### 2.216 Jetty清理阶段下层释放操作失败
* 故障编号：urma_266
* 故障现象：
    * 关键日志：匹配`urma_set_jetty_opt`，匹配`Failed to exec urma_delete_jetty_to_jetty_grp.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_set_jetty_opt
#### 2.217 设置Jetty过程中依赖步骤失败
* 故障编号：urma_267
* 故障现象：
    * 关键日志：匹配`urma_set_jetty_opt`，匹配`Failed to exec urma_jetty_set_options.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_jetty_opt
#### 2.218 设置设备过程中依赖步骤失败
* 故障编号：urma_268
* 故障现象：
    * 关键日志：匹配`urma_set_jetty_opt`，匹配`UB dev should use share jfr!`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_jetty_opt
#### 2.219 设置Jetty过程中依赖步骤失败
* 故障编号：urma_269
* 故障现象：
    * 关键日志：匹配`urma_set_jetty_opt`，匹配`Failed to exec ops->set_jetty_opt.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_jetty_opt
#### 2.220 设置Jetty过程中依赖步骤失败
* 故障编号：urma_270
* 故障现象：
    * 关键日志：匹配`urma_set_jetty_opt`，匹配`Failed to exec urma_add_jetty_to_jetty_grp.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_jetty_opt
#### 2.221 Jetty对象无效导致获取Jetty失败
* 故障编号：urma_271
* 故障现象：
    * 关键日志：匹配`urma_get_jetty_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取Jetty，调用方传入的Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_jetty_opt
#### 2.222 URMA context、provider操作表、Jetty对象、provider未提供get_jetty_opt操作实现无效导致获取Jetty失败
* 故障编号：urma_272
* 故障现象：
    * 关键日志：匹配`urma_get_jetty_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取Jetty，调用方传入的URMA context、provider操作表、Jetty对象、provider未提供get_jetty_opt操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_jetty_opt
#### 2.223 获取Jetty过程中依赖步骤失败
* 故障编号：urma_273
* 故障现象：
    * 关键日志：匹配`urma_get_jetty_opt`，匹配`Failed to exec ops->get_jetty_opt.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_get_jetty_opt
#### 2.224 provider操作表、Jetty对象无效导致激活Jetty失败
* 故障编号：urma_274
* 故障现象：
    * 关键日志：匹配`urma_active_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活Jetty，调用方传入的provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_active_jetty
#### 2.225 URMA context、provider操作表、Jetty对象无效导致激活Jetty失败
* 故障编号：urma_275
* 故障现象：
    * 关键日志：匹配`urma_active_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活Jetty，调用方传入的URMA context、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_active_jetty
#### 2.226 URMA context、provider操作表、Jetty对象无效导致激活Jetty失败
* 故障编号：urma_276
* 故障现象：
    * 关键日志：匹配`urma_active_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活Jetty，调用方传入的URMA context、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_active_jetty
#### 2.227 URMA context无效导致激活Jetty失败
* 故障编号：urma_277
* 故障现象：
    * 关键日志：匹配`urma_active_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活Jetty，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_active_jetty
#### 2.228 Jetty数据通路处理失败
* 故障编号：urma_278
* 故障现象：
    * 关键日志：匹配`urma_active_jetty`，匹配`Jetty state is wrong in active_jetty.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：urma_active_jetty
#### 2.229 激活JFC过程中依赖步骤失败
* 故障编号：urma_279
* 故障现象：
    * 关键日志：匹配`urma_active_jetty`，匹配`jfc or jfr has not activated.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_active_jetty
#### 2.230 URMA context、provider操作表、JFR对象、Jetty对象、provider未提供active_jetty操作实现无效导致激活Jetty失败
* 故障编号：urma_280
* 故障现象：
    * 关键日志：匹配`urma_active_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活Jetty，调用方传入的URMA context、provider操作表、JFR对象、Jetty对象、provider未提供active_jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_active_jetty
#### 2.231 激活Jetty过程中依赖步骤失败
* 故障编号：urma_281
* 故障现象：
    * 关键日志：匹配`urma_active_jetty`，匹配`Failed to exec ops->active_jetty.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_active_jetty
#### 2.232 provider操作表、Jetty对象无效导致去激活Jetty失败
* 故障编号：urma_282
* 故障现象：
    * 关键日志：匹配`urma_deactive_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活Jetty，调用方传入的provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jetty
#### 2.233 Jetty数据通路处理失败
* 故障编号：urma_283
* 故障现象：
    * 关键日志：匹配`urma_deactive_jetty`，匹配`Jetty state is wrong in deactive_jetty.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：urma_deactive_jetty
#### 2.234 URMA context、provider操作表、Jetty对象、provider未提供deactive_jetty操作实现无效导致去激活Jetty失败
* 故障编号：urma_284
* 故障现象：
    * 关键日志：匹配`urma_deactive_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活Jetty，调用方传入的URMA context、provider操作表、Jetty对象、provider未提供deactive_jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jetty
#### 2.235 去激活Jetty过程中依赖步骤失败
* 故障编号：urma_285
* 故障现象：
    * 关键日志：匹配`urma_deactive_jetty`，匹配`Failed to exec ops->deactive_jetty.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_deactive_jetty
#### 2.236 URMA context、provider操作表、Jetty对象无效导致去激活Jetty失败
* 故障编号：urma_286
* 故障现象：
    * 关键日志：匹配`urma_deactive_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活Jetty，调用方传入的URMA context、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jetty
#### 2.237 URMA context、provider操作表、provider未提供create_notifier操作实现无效导致去激活Jetty失败
* 故障编号：urma_287
* 故障现象：
    * 关键日志：匹配`urma_deactive_jetty`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活Jetty，调用方传入的URMA context、provider操作表、provider未提供create_notifier操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jetty
#### 2.238 Notifier相关临时结构或命令参数分配失败
* 故障编号：urma_288
* 故障现象：
    * 关键日志：匹配`urma_deactive_jetty`，匹配`Failed to alloc notifier.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配Notifier前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_deactive_jetty
#### 2.239 确认Jetty过程中依赖步骤失败
* 故障编号：urma_289
* 故障现象：
    * 关键日志：匹配`urma_ack_notify`，匹配`max_jetty_in_jetty_grp`，匹配`is err.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于确认Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_ack_notify
#### 2.240 Jetty创建时下层资源准备失败
* 故障编号：urma_290
* 故障现象：
    * 关键日志：匹配`urma_ack_notify`，匹配`create_jetty_grp failed.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：urma_ack_notify
#### 2.241 Jetty相关临时结构或命令参数分配失败
* 故障编号：urma_291
* 故障现象：
    * 关键日志：匹配`urma_ack_notify`，匹配`alloc jetty list failed.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_ack_notify
#### 2.242 Jetty清理阶段下层释放操作失败
* 故障编号：urma_292
* 故障现象：
    * 关键日志：匹配`urma_ack_notify`，匹配`delete_jetty_grp failed.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_ack_notify
#### 2.243 URMA context无效导致删除Jetty失败
* 故障编号：urma_293
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_grp`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jetty_grp
#### 2.244 URMA context、provider操作表、provider未提供delete_jetty_grp操作实现无效导致删除Jetty失败
* 故障编号：urma_294
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_grp`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的URMA context、provider操作表、provider未提供delete_jetty_grp操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jetty_grp
#### 2.245 URMA context、provider操作表无效导致删除Jetty失败
* 故障编号：urma_295
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_grp`，匹配`Invalid parameter: jetty_list`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jetty_grp
#### 2.246 删除Jetty过程中依赖步骤失败
* 故障编号：urma_296
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_grp`，匹配`jetty grp in use, jetty_cnt:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_delete_jetty_grp
#### 2.247 URMA context、provider操作表、Segment对象无效导致删除Jetty失败
* 故障编号：urma_297
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_grp`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的URMA context、provider操作表、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jetty_grp
#### 2.248 设置Token过程中依赖步骤失败
* 故障编号：urma_298
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_grp`，匹配`Token value must be set when token policy is not URMA_TOKEN_NONE.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Token，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_delete_jetty_grp
#### 2.249 URMA context、provider操作表、Segment对象、provider未提供import_seg操作实现无效导致删除Jetty失败
* 故障编号：urma_299
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_grp`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Jetty，调用方传入的URMA context、provider操作表、Segment对象、provider未提供import_seg操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jetty_grp
#### 2.250 Segment导入时下层资源准备失败
* 故障编号：urma_300
* 故障现象：
    * 关键日志：匹配`urma_delete_jetty_grp`，匹配`[DRV_ERR]Failed to import seg, dev_name:`，匹配`, eid_idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责导入Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：urma_delete_jetty_grp
#### 2.251 URMA context、Jetty对象无效导致获取TPN失败
* 故障编号：urma_301
* 故障现象：
    * 关键日志：匹配`urma_get_tpn`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取TPN，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_tpn
#### 2.252 URMA context、provider操作表、Jetty对象、provider未提供get_tpn操作实现无效导致获取TPN失败
* 故障编号：urma_302
* 故障现象：
    * 关键日志：匹配`urma_get_tpn`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取TPN，调用方传入的URMA context、provider操作表、Jetty对象、provider未提供get_tpn操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_tpn
#### 2.253 URMA context、设备对象、sysfs设备信息、provider操作表、Jetty对象无效导致获取TPN失败
* 故障编号：urma_303
* 故障现象：
    * 关键日志：匹配`urma_get_tpn`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取TPN，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_tpn
#### 2.254 URMA context、设备对象、sysfs设备信息无效导致获取TPN失败
* 故障编号：urma_304
* 故障现象：
    * 关键日志：匹配`urma_get_tpn`，匹配`Invalid parameter with max_netaddr_cnt as 0.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取TPN，调用方传入的URMA context、设备对象、sysfs设备信息不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_tpn
#### 2.255 获取TPN过程中依赖步骤失败
* 故障编号：urma_305
* 故障现象：
    * 关键日志：匹配`urma_get_tpn`，匹配`Failed to get netaddr list, ret:`，匹配`, max_netaddr_cnt:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取TPN，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_get_tpn
#### 2.256 URMA context、provider操作表无效导致修改TP失败
* 故障编号：urma_306
* 故障现象：
    * 关键日志：匹配`urma_modify_tp`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改TP，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_modify_tp
#### 2.257 URMA context、provider操作表、provider未提供modify_tp操作实现无效导致修改TP失败
* 故障编号：urma_307
* 故障现象：
    * 关键日志：匹配`urma_modify_tp`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改TP，调用方传入的URMA context、provider操作表、provider未提供modify_tp操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_modify_tp
#### 2.258 URMA context、provider操作表无效导致获取TP失败
* 故障编号：urma_308
* 故障现象：
    * 关键日志：匹配`urma_get_tp_list`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取TP，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_tp_list
#### 2.259 URMA context、provider操作表无效导致获取TP失败
* 故障编号：urma_309
* 故障现象：
    * 关键日志：匹配`urma_get_tp_list`，匹配`Invalid parameter, trans_mode:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取TP，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_tp_list
#### 2.260 URMA context、provider操作表、provider未提供get_tp_list操作实现无效导致获取TP失败
* 故障编号：urma_310
* 故障现象：
    * 关键日志：匹配`urma_get_tp_list`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取TP，调用方传入的URMA context、provider操作表、provider未提供get_tp_list操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_tp_list
#### 2.261 URMA context、provider操作表无效导致设置TP失败
* 故障编号：urma_311
* 故障现象：
    * 关键日志：匹配`urma_set_tp_attr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置TP，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_tp_attr
#### 2.262 URMA context、provider操作表、provider未提供set_tp_attr操作实现无效导致设置TP失败
* 故障编号：urma_312
* 故障现象：
    * 关键日志：匹配`urma_set_tp_attr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置TP，调用方传入的URMA context、provider操作表、provider未提供set_tp_attr操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_tp_attr
#### 2.263 URMA context、provider操作表无效导致获取TP失败
* 故障编号：urma_313
* 故障现象：
    * 关键日志：匹配`urma_get_tp_attr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取TP，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_tp_attr
#### 2.264 URMA context、provider操作表、provider未提供get_tp_attr操作实现无效导致获取TP失败
* 故障编号：urma_314
* 故障现象：
    * 关键日志：匹配`urma_get_tp_attr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取TP，调用方传入的URMA context、provider操作表、provider未提供get_tp_attr操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_tp_attr
#### 2.265 设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败
* 故障编号：urma_315
* 故障现象：
    * 关键日志：匹配`urma_parse_rsvd_jetty_range`，匹配`parse sysfs:`，匹配`failed`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_parse_rsvd_jetty_range
#### 2.266 端口信息的sysfs读取或解析失败
* 故障编号：urma_316
* 故障现象：
    * 关键日志：匹配`urma_parse_rsvd_jetty_range`，匹配`parse rsvd jetty:`，匹配`failed`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取端口信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_parse_rsvd_jetty_range
#### 2.267 Jetty对象、WR对象无效导致投递Jetty失败
* 故障编号：urma_317
* 故障现象：
    * 关键日志：匹配`urma_post_jetty_send_wr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于投递Jetty，调用方传入的Jetty对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_post_jetty_send_wr
#### 2.268 Jetty对象、WR对象无效导致投递Jetty失败
* 故障编号：urma_318
* 故障现象：
    * 关键日志：匹配`urma_post_jetty_recv_wr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于投递Jetty，调用方传入的Jetty对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_post_jetty_recv_wr

## 3 资源创建失败
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 3.1 epoll创建时下层资源准备失败
* 故障编号：urma_319
* 故障现象：
    * 关键日志：匹配`bondp_create_pjfce`，匹配`Failed to create pjfce`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建epoll，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_pjfce
#### 3.2 文件描述符数据通路处理失败
* 故障编号：urma_320
* 故障现象：
    * 关键日志：匹配`bondp_create_pjfce`，匹配`Fail to add fd:`，匹配`to epoll fd:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_create_pjfce
#### 3.3 epoll创建时下层资源准备失败
* 故障编号：urma_321
* 故障现象：
    * 关键日志：匹配`bondp_create_vjfce`，匹配`Fail to create epoll_fd for vjfce.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建epoll，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_vjfce
#### 3.4 context创建时下层资源准备失败
* 故障编号：urma_322
* 故障现象：
    * 关键日志：匹配`bondp_delete_vjfce`，匹配`Failed to create vjfce.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_delete_vjfce
#### 3.5 JFCE创建时下层资源准备失败
* 故障编号：urma_323
* 故障现象：
    * 关键日志：匹配`bondp_delete_vjfce`，匹配`Failed to create pjfce.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建JFCE，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_delete_vjfce
#### 3.6 物理 JFC创建时下层资源准备失败
* 故障编号：urma_324
* 故障现象：
    * 关键日志：匹配`bondp_create_pjfc`，匹配`Failed to create pjfc`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建物理 JFC，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_pjfc
#### 3.7 物理 JFC创建时下层资源准备失败
* 故障编号：urma_325
* 故障现象：
    * 关键日志：匹配`bondp_delete_pjfc`，匹配`Failed to create pjfc`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建物理 JFC，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_delete_pjfc
#### 3.8 虚拟 JFC创建时下层资源准备失败
* 故障编号：urma_326
* 故障现象：
    * 关键日志：匹配`bondp_delete_pjfc`，匹配`Failed to create vjfc, dev_name:`，匹配`, eid_idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建虚拟 JFC，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_delete_pjfc
#### 3.9 JFS创建时下层资源准备失败
* 故障编号：urma_327
* 故障现象：
    * 关键日志：匹配`bondp_create_vjfs`，匹配`ubcore create jfs failed.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建JFS，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_vjfs
#### 3.10 物理 JFS创建时下层资源准备失败
* 故障编号：urma_328
* 故障现象：
    * 关键日志：匹配`bondp_create_pjfs`，匹配`Failed to create pjfs`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建物理 JFS，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_pjfs
#### 3.11 物理 JFR创建时下层资源准备失败
* 故障编号：urma_329
* 故障现象：
    * 关键日志：匹配`bondp_create_pjfr`，匹配`Failed to create pjfr`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建物理 JFR，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_pjfr
#### 3.12 未找到可用于释放Token的有效对象或路由
* 故障编号：urma_330
* 故障现象：
    * 关键日志：匹配`bdp_r_v2p_token_id_del_idx_lockless`，匹配`Failed to find node, index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在释放Token过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位目标。
* 解决办法：无
* 函数名：bdp_r_v2p_token_id_del_idx_lockless
#### 3.13 JFS相关临时结构或命令参数分配失败
* 故障编号：urma_331
* 故障现象：
    * 关键日志：匹配`bondp_post_send_wr_and_store`，匹配`Failed to allocate jfs wr entry`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在投递JFS前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：bondp_post_send_wr_and_store
#### 3.14 JFR相关临时结构或命令参数分配失败
* 故障编号：urma_332
* 故障现象：
    * 关键日志：匹配`bondp_post_recv_wr_and_store`，匹配`Failed to allocate jfr wr entry`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在投递JFR前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：bondp_post_recv_wr_and_store
#### 3.15 健康检查相关临时结构或命令参数分配失败
* 故障编号：urma_333
* 故障现象：
    * 关键日志：匹配`bondp_register_health_ctx_global`，匹配`Failed to alloc health ctx node`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配健康检查前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：bondp_register_health_ctx_global
#### 3.16 健康检查创建时下层资源准备失败
* 故障编号：urma_334
* 故障现象：
    * 关键日志：匹配`bondp_start_health_check_thread`，匹配`Failed to create health epoll`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_start_health_check_thread
#### 3.17 设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败
* 故障编号：urma_335
* 故障现象：
    * 关键日志：匹配`bondp_start_health_check_thread`，匹配`Failed to create health check thread`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：bondp_start_health_check_thread
#### 3.18 健康检查创建时下层资源准备失败
* 故障编号：urma_336
* 故障现象：
    * 关键日志：匹配`bondp_create_health_check_ctx`，匹配`Failed to create health task table`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_health_check_ctx
#### 3.19 健康检查创建时下层资源准备失败
* 故障编号：urma_337
* 故障现象：
    * 关键日志：匹配`bondp_create_health_check_ctx`，匹配`Failed to create health_check_fd, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_health_check_ctx
#### 3.20 context数据通路处理失败
* 故障编号：urma_338
* 故障现象：
    * 关键日志：匹配`bondp_create_health_check_ctx`，匹配`Failed to add ctx async fd to health epoll, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_create_health_check_ctx
#### 3.21 健康检查注册时下层资源准备失败
* 故障编号：urma_339
* 故障现象：
    * 关键日志：匹配`bondp_create_health_check_ctx`，匹配`Failed to register health ctx globally`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责注册健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_health_check_ctx
#### 3.22 context创建时下层资源准备失败
* 故障编号：urma_340
* 故障现象：
    * 关键日志：匹配`get_topo_info_from_ko`，匹配`Failed to create topo map`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：get_topo_info_from_ko
#### 3.23 Token创建时下层资源准备失败
* 故障编号：urma_341
* 故障现象：
    * 关键日志：匹配`bondp_create_vcontext`，匹配`Failed to create remote_v2p_token_id_table`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建Token，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_vcontext
#### 3.24 context创建时下层资源准备失败
* 故障编号：urma_342
* 故障现象：
    * 关键日志：匹配`bondp_create_vcontext`，匹配`Failed to create context, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_vcontext
#### 3.25 epoll创建时下层资源准备失败
* 故障编号：urma_343
* 故障现象：
    * 关键日志：匹配`bondp_create_vcontext`，匹配`Failed to create epoll`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建epoll，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_vcontext
#### 3.26 context创建时下层资源准备失败
* 故障编号：urma_344
* 故障现象：
    * 关键日志：匹配`bondp_create_pcontext`，匹配`Failed to create context for primary eid, dev:`，匹配`, eid_idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_pcontext
#### 3.27 创建文件描述符过程中依赖步骤失败
* 故障编号：urma_345
* 故障现象：
    * 关键日志：匹配`bondp_create_pcontext`，匹配`failed to add fd:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建文件描述符，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_create_pcontext
#### 3.28 context创建时下层资源准备失败
* 故障编号：urma_346
* 故障现象：
    * 关键日志：匹配`bondp_delete_pcontext`，匹配`Failed to create ctx`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_delete_pcontext
#### 3.29 context创建时下层资源准备失败
* 故障编号：urma_347
* 故障现象：
    * 关键日志：匹配`bondp_delete_pcontext`，匹配`Failed to create vcontext`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_delete_pcontext
#### 3.30 context创建时下层资源准备失败
* 故障编号：urma_348
* 故障现象：
    * 关键日志：匹配`bondp_delete_pcontext`，匹配`Failed to create pctx`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_delete_pcontext
#### 3.31 健康检查创建时下层资源准备失败
* 故障编号：urma_349
* 故障现象：
    * 关键日志：匹配`bondp_delete_pcontext`，匹配`Failed to create health check scene`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_delete_pcontext
#### 3.32 context创建时下层资源准备失败
* 故障编号：urma_350
* 故障现象：
    * 关键日志：匹配`bondp_set_bonding_mode`，匹配`Failed to create pctx when set bonding mode, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_set_bonding_mode
#### 3.33 执行URMA资源所需输入对象无效导致创建URMA资源失败
* 故障编号：urma_351
* 故障现象：
    * 关键日志：匹配`update_mapping_hash_table`，匹配`Invalid topo info to create topo map`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建URMA资源，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：update_mapping_hash_table
#### 3.34 URMA资源相关临时结构或命令参数分配失败
* 故障编号：urma_352
* 故障现象：
    * 关键日志：匹配`update_mapping_hash_table`，匹配`Failed to alloc topo_map`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配URMA资源前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：update_mapping_hash_table
#### 3.35 EID创建时下层资源准备失败
* 故障编号：urma_353
* 故障现象：
    * 关键日志：匹配`update_mapping_hash_table`，匹配`Failed to create eid_mapping_hash_table`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建EID，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：update_mapping_hash_table
#### 3.36 URMA context、设备对象、provider操作表无效导致创建context失败
* 故障编号：urma_354
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_context`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建context，调用方传入的URMA context、设备对象、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_create_context
#### 3.37 查询EID过程中依赖步骤失败
* 故障编号：urma_355
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_context`，匹配`Failed to query eid.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_create_context
#### 3.38 创建ioctl的ioctl调用返回失败
* 故障编号：urma_356
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_context`，匹配`ioctl failed, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交创建ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_create_context
#### 3.39 URMA context、Segment对象无效导致分配Token失败
* 故障编号：urma_357
* 故障现象：
    * 关键日志：匹配`urma_cmd_alloc_token_id`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配Token，调用方传入的URMA context、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_alloc_token_id
#### 3.40 ioctl相关临时结构或命令参数分配失败
* 故障编号：urma_358
* 故障现象：
    * 关键日志：匹配`urma_cmd_alloc_token_id`，匹配`ioctl failed in urma_cmd_alloc_token_id, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配ioctl前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_cmd_alloc_token_id
#### 3.41 URMA context无效导致分配Token失败
* 故障编号：urma_359
* 故障现象：
    * 关键日志：匹配`urma_cmd_alloc_token_id_ex`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配Token，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_alloc_token_id_ex
#### 3.42 ioctl相关临时结构或命令参数分配失败
* 故障编号：urma_360
* 故障现象：
    * 关键日志：匹配`urma_cmd_alloc_token_id_ex`，匹配`ioctl failed in urma_cmd_alloc_token_id, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配ioctl前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_cmd_alloc_token_id_ex
#### 3.43 URMA context无效导致释放Token失败
* 故障编号：urma_361
* 故障现象：
    * 关键日志：匹配`urma_cmd_free_token_id`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放Token，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_free_token_id
#### 3.44 释放ioctl的ioctl调用返回失败
* 故障编号：urma_362
* 故障现象：
    * 关键日志：匹配`urma_cmd_free_token_id`，匹配`ioctl failed, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交释放ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_free_token_id
#### 3.45 URMA context、JFS对象、目标Jetty对象无效导致创建JFS失败
* 故障编号：urma_363
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_jfs`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFS，调用方传入的URMA context、JFS对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_create_jfs
#### 3.46 创建ioctl的ioctl调用返回失败
* 故障编号：urma_364
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_jfs`，匹配`ioctl failed, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交创建ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_create_jfs
#### 3.47 JFS相关临时结构或命令参数分配失败
* 故障编号：urma_365
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfs_batch`，匹配`Failed to malloc buffer.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在删除JFS前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_cmd_delete_jfs_batch
#### 3.48 URMA context、JFR对象无效导致创建JFR失败
* 故障编号：urma_366
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_jfr`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_create_jfr
#### 3.49 创建ioctl的ioctl调用返回失败
* 故障编号：urma_367
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_jfr`，匹配`ioctl failed in urma_cmd_create_jfr, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交创建ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_create_jfr
#### 3.50 URMA context、JFS对象、JFR对象无效导致分配JFS失败
* 故障编号：urma_368
* 故障现象：
    * 关键日志：匹配`urma_cmd_alloc_jfs`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配JFS，调用方传入的URMA context、JFS对象、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_alloc_jfs
#### 3.51 ioctl相关临时结构或命令参数分配失败
* 故障编号：urma_369
* 故障现象：
    * 关键日志：匹配`urma_cmd_alloc_jfs`，匹配`ioctl failed in urma_cmd_alloc_jfr, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配ioctl前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_cmd_alloc_jfs
#### 3.52 JFR相关临时结构或命令参数分配失败
* 故障编号：urma_370
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfr_batch`，匹配`Failed to malloc buffer.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在删除JFR前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_cmd_delete_jfr_batch
#### 3.53 URMA context无效导致创建JFC失败
* 故障编号：urma_371
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_jfc`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_create_jfc
#### 3.54 创建ioctl的ioctl调用返回失败
* 故障编号：urma_372
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_jfc`，匹配`ioctl failed in urma_cmd_create_jfc, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交创建ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_create_jfc
#### 3.55 JFC相关临时结构或命令参数分配失败
* 故障编号：urma_373
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfc_batch`，匹配`Failed to malloc buffer.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在删除JFC前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_cmd_delete_jfc_batch
#### 3.56 URMA context无效导致分配JFC失败
* 故障编号：urma_374
* 故障现象：
    * 关键日志：匹配`urma_cmd_alloc_jfc`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_alloc_jfc
#### 3.57 ioctl相关临时结构或命令参数分配失败
* 故障编号：urma_375
* 故障现象：
    * 关键日志：匹配`urma_cmd_alloc_jfc`，匹配`ioctl failed in urma_cmd_alloc_jfc, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配ioctl前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_cmd_alloc_jfc
#### 3.58 URMA context无效导致创建JFCE失败
* 故障编号：urma_376
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_jfce`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFCE，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_create_jfce
#### 3.59 创建ioctl的ioctl调用返回失败
* 故障编号：urma_377
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_jfce`，匹配`ioctl failed in urma_cmd_create_jfce, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交创建ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_create_jfce
#### 3.60 URMA context、JFR对象、Jetty对象、目标Jetty对象无效导致分配JFR失败
* 故障编号：urma_378
* 故障现象：
    * 关键日志：匹配`urma_cmd_alloc_jfr`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配JFR，调用方传入的URMA context、JFR对象、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_alloc_jfr
#### 3.61 ioctl相关临时结构或命令参数分配失败
* 故障编号：urma_379
* 故障现象：
    * 关键日志：匹配`urma_cmd_alloc_jfr`，匹配`ioctl failed in urma_cmd_alloc_jfr, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配ioctl前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_cmd_alloc_jfr
#### 3.62 URMA context、Jetty对象无效导致创建Notifier失败
* 故障编号：urma_380
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_notifier`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建Notifier，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_create_notifier
#### 3.63 创建ioctl的ioctl调用返回失败
* 故障编号：urma_381
* 故障现象：
    * 关键日志：匹配`urma_cmd_create_notifier`，匹配`ioctl failed in urma_cmd_create_notifier, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交创建ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_create_notifier
#### 3.64 JFC创建时下层资源准备失败
* 故障编号：urma_382
* 故障现象：
    * 关键日志：匹配`urma_check_trans_mode_valid`，匹配`[DRV_ERR]Failed to create jfc, dev_name:`，匹配`, eid_idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建JFC，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：urma_check_trans_mode_valid
#### 3.65 JFC相关临时结构或命令参数分配失败
* 故障编号：urma_383
* 故障现象：
    * 关键日志：匹配`urma_delete_jfc_batch`，匹配`Failed to alloc memory.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配JFC前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_delete_jfc_batch
#### 3.66 JFC相关临时结构或命令参数分配失败
* 故障编号：urma_384
* 故障现象：
    * 关键日志：匹配`urma_delete_jfc_batch`，匹配`Failed to alloc memory.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配JFC前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_delete_jfc_batch
#### 3.67 URMA context、provider操作表无效导致分配JFC失败
* 故障编号：urma_385
* 故障现象：
    * 关键日志：匹配`urma_alloc_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配JFC，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_alloc_jfc
#### 3.68 URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_jfc操作实现无效导致分配JFC失败
* 故障编号：urma_386
* 故障现象：
    * 关键日志：匹配`urma_alloc_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配JFC，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_jfc操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_alloc_jfc
#### 3.69 分配JFC过程中依赖步骤失败
* 故障编号：urma_387
* 故障现象：
    * 关键日志：匹配`urma_alloc_jfc`，匹配`jfc cfg depth of range, depth:`，匹配`, max_depth:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_alloc_jfc
#### 3.70 JFC相关临时结构或命令参数分配失败
* 故障编号：urma_388
* 故障现象：
    * 关键日志：匹配`urma_alloc_jfc`，匹配`failed to exec ops->alloc_jfc`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配JFC前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_alloc_jfc
#### 3.71 JFS创建时下层资源准备失败
* 故障编号：urma_389
* 故障现象：
    * 关键日志：匹配`urma_check_order_type`，匹配`[DRV_ERR]Failed to create jfs, dev_name:`，匹配`, eid_idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建JFS，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：urma_check_order_type
#### 3.72 JFS相关临时结构或命令参数分配失败
* 故障编号：urma_390
* 故障现象：
    * 关键日志：匹配`urma_delete_jfs_batch`，匹配`Failed to alloc memory.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配JFS前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_delete_jfs_batch
#### 3.73 URMA context、provider操作表、JFS对象无效导致分配JFS失败
* 故障编号：urma_391
* 故障现象：
    * 关键日志：匹配`urma_alloc_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配JFS，调用方传入的URMA context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_alloc_jfs
#### 3.74 URMA context、provider操作表、JFS对象无效导致分配JFS失败
* 故障编号：urma_392
* 故障现象：
    * 关键日志：匹配`urma_alloc_jfs`，匹配`Invalid parameter, trans_mode:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配JFS，调用方传入的URMA context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_alloc_jfs
#### 3.75 URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_jfs操作实现无效导致分配JFS失败
* 故障编号：urma_393
* 故障现象：
    * 关键日志：匹配`urma_alloc_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配JFS，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_alloc_jfs
#### 3.76 分配JFS过程中依赖步骤失败
* 故障编号：urma_394
* 故障现象：
    * 关键日志：匹配`urma_alloc_jfs`，匹配`jfs cfg out of range, depth:`，匹配`, max_depth:`，匹配`, inline_data:`，匹配`, max_inline_len:`，匹配`, sge:`，匹配`hu, max_sge:`，匹配`, rsge:`，匹配`hu, max_rsge:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_alloc_jfs
#### 3.77 JFR创建时下层资源准备失败
* 故障编号：urma_395
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfs`，匹配`[DRV_ERR]Failed to create jfr, dev_name:`，匹配`, eid_idex:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建JFR，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：urma_deactive_jfs
#### 3.78 JFR相关临时结构或命令参数分配失败
* 故障编号：urma_396
* 故障现象：
    * 关键日志：匹配`urma_delete_jfr_batch`，匹配`Failed to alloc memory.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配JFR前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：urma_delete_jfr_batch
#### 3.79 设置Token过程中依赖步骤失败
* 故障编号：urma_397
* 故障现象：
    * 关键日志：匹配`urma_check_ctrlplane_compat`，匹配`Token value must be set when token policy is not URMA_TOKEN_NONE.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Token，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_check_ctrlplane_compat
#### 3.80 URMA context、provider操作表、JFR对象无效导致分配JFR失败
* 故障编号：urma_398
* 故障现象：
    * 关键日志：匹配`urma_alloc_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配JFR，调用方传入的URMA context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_alloc_jfr
#### 3.81 URMA context、provider操作表、JFR对象无效导致分配JFR失败
* 故障编号：urma_399
* 故障现象：
    * 关键日志：匹配`urma_alloc_jfr`，匹配`Invalid parameter, trans_mode:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配JFR，调用方传入的URMA context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_alloc_jfr
#### 3.82 URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_jfr操作实现无效导致分配JFR失败
* 故障编号：urma_400
* 故障现象：
    * 关键日志：匹配`urma_alloc_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配JFR，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_alloc_jfr
#### 3.83 分配JFR过程中依赖步骤失败
* 故障编号：urma_401
* 故障现象：
    * 关键日志：匹配`urma_alloc_jfr`，匹配`jfr cfg out of range, depth:`，匹配`, max_depth:`，匹配`, sge:`，匹配`, max_sge:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_alloc_jfr
#### 3.84 JFCE创建时下层资源准备失败
* 故障编号：urma_402
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfr`，匹配`[DRV_ERR]Failed to create jfce, dev_name:`，匹配`, eid_idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建JFCE，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：urma_deactive_jfr
#### 3.85 URMA context、provider操作表无效导致释放Token失败
* 故障编号：urma_403
* 故障现象：
    * 关键日志：匹配`urma_free_token_id`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放Token，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_free_token_id
#### 3.86 释放Token过程中依赖步骤失败
* 故障编号：urma_404
* 故障现象：
    * 关键日志：匹配`urma_free_token_id`，匹配`ref:`，匹配`u, not zero`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放Token，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_free_token_id
#### 3.87 URMA context、provider操作表、provider未提供free_token_id操作实现无效导致释放Token失败
* 故障编号：urma_405
* 故障现象：
    * 关键日志：匹配`urma_free_token_id`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放Token，调用方传入的URMA context、provider操作表、provider未提供free_token_id操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_free_token_id
#### 3.88 Token清理阶段下层释放操作失败
* 故障编号：urma_406
* 故障现象：
    * 关键日志：匹配`urma_free_token_id`，匹配`[DRV_ERR]Failed to free token_id, dev_name:`，匹配`, eid_idx:`，匹配`, tid:`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Token相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_free_token_id
#### 3.89 注册URMA资源所需输入对象无效导致注册URMA资源失败
* 故障编号：urma_407
* 故障现象：
    * 关键日志：匹配`urma_register_log_func`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于注册URMA资源，调用方传入的注册URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：当前不会触发失败
* 函数名：urma_register_log_func
#### 3.90 context创建时下层资源准备失败
* 故障编号：urma_408
* 故障现象：
    * 关键日志：匹配`urma_query_eid`，匹配`[DRV_ERR]Failed to create urma context.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：urma_query_eid
#### 3.91 设备注册时下层资源准备失败
* 故障编号：urma_409
* 故障现象：
    * 关键日志：匹配`urma_register_sysfs_dev`，匹配`Register device failed. Failed to match driver for device`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责注册设备，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：urma_register_sysfs_dev

## 4 资源查询失败
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 4.1 查询物理 JFR过程中依赖步骤失败
* 故障编号：urma_410
* 故障现象：
    * 关键日志：匹配`bondp_query_jfr`，匹配`query pjfr fail, index:`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询物理 JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_query_jfr
#### 4.2 URMA context无效导致查询端口失败
* 故障编号：urma_411
* 故障现象：
    * 关键日志：匹配`bondp_user_ctl_query_port`，匹配`Invalid query port param.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询端口，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_user_ctl_query_port
#### 4.3 URMA context、JFR对象无效导致查询JFR失败
* 故障编号：urma_412
* 故障现象：
    * 关键日志：匹配`bondp_user_ctl_query_port`，匹配`Invalid jfr.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_user_ctl_query_port
#### 4.4 查询context过程中依赖步骤失败
* 故障编号：urma_413
* 故障现象：
    * 关键日志：匹配`bondp_user_ctl_query_port`，匹配`The object does not belong to current context.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_user_ctl_query_port
#### 4.5 URMA context无效导致获取EID失败
* 故障编号：urma_414
* 故障现象：
    * 关键日志：匹配`bondp_get_async_event`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取EID，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_get_async_event
#### 4.6 epoll数据通路处理失败
* 故障编号：urma_415
* 故障现象：
    * 关键日志：匹配`bondp_get_async_event`，匹配`epoll_wait no event or err.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_get_async_event
#### 4.7 epoll数据通路处理失败
* 故障编号：urma_416
* 故障现象：
    * 关键日志：匹配`bondp_get_async_event`，匹配`bondp get error epoll_event: 0x`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_get_async_event
#### 4.8 获取组件过程中依赖步骤失败
* 故障编号：urma_417
* 故障现象：
    * 关键日志：匹配`resend_jfs_wr`，匹配`Failed to get comp, local_id:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取组件，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：resend_jfs_wr
#### 4.9 未找到可用于修改端口的有效对象或路由
* 故障编号：urma_418
* 故障现象：
    * 关键日志：匹配`handle_send_cr_with_store`，匹配`Failed to find valid port for retransmission.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在修改端口过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位目标。
* 解决办法：无
* 函数名：handle_send_cr_with_store
#### 4.10 获取context过程中依赖步骤失败
* 故障编号：urma_419
* 故障现象：
    * 关键日志：匹配`get_topo_info_from_ko`，匹配`Failed to get topo info, change to general mode`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：get_topo_info_from_ko
#### 4.11 获取健康检查过程中依赖步骤失败
* 故障编号：urma_420
* 故障现象：
    * 关键日志：匹配`bondp_delete_pcontext`，匹配`Failed to get topo info, change to general mode`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取健康检查，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_delete_pcontext
#### 4.12 获取EID所需输入对象无效导致获取EID失败
* 故障编号：urma_421
* 故障现象：
    * 关键日志：匹配`get_bonding_eid_by_target_eid`，匹配`Invalid param`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取EID，调用方传入的获取EID所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：get_bonding_eid_by_target_eid
#### 4.13 URMA context、JFS对象无效导致查询JFS失败
* 故障编号：urma_422
* 故障现象：
    * 关键日志：匹配`urma_cmd_query_jfs`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_query_jfs
#### 4.14 查询ioctl的ioctl调用返回失败
* 故障编号：urma_423
* 故障现象：
    * 关键日志：匹配`urma_cmd_query_jfs`，匹配`ioctl failed, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交查询ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_query_jfs
#### 4.15 URMA context、JFS对象无效导致获取JFS失败
* 故障编号：urma_424
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfs_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_jfs_opt
#### 4.16 URMA context、JFS对象无效导致获取JFS失败
* 故障编号：urma_425
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfs_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_jfs_opt
#### 4.17 获取ioctl的ioctl调用返回失败
* 故障编号：urma_426
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfs_opt`，匹配`ioctl failed in urma_cmd_get_jfs_opt, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交获取ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_get_jfs_opt
#### 4.18 URMA context无效导致获取JFS失败
* 故障编号：urma_427
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfs_opt`，匹配`Invalid out buffer from kernel.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFS，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_jfs_opt
#### 4.19 URMA context、JFR对象无效导致查询JFR失败
* 故障编号：urma_428
* 故障现象：
    * 关键日志：匹配`urma_cmd_query_jfr`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_query_jfr
#### 4.20 查询ioctl的ioctl调用返回失败
* 故障编号：urma_429
* 故障现象：
    * 关键日志：匹配`urma_cmd_query_jfr`，匹配`ioctl failed, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交查询ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_query_jfr
#### 4.21 URMA context无效导致获取JFC失败
* 故障编号：urma_430
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfc_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_jfc_opt
#### 4.22 URMA context无效导致获取JFC失败
* 故障编号：urma_431
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfc_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_jfc_opt
#### 4.23 获取ioctl的ioctl调用返回失败
* 故障编号：urma_432
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfc_opt`，匹配`ioctl failed in urma_cmd_get_jfc_opt, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交获取ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_get_jfc_opt
#### 4.24 URMA context无效导致获取JFC失败
* 故障编号：urma_433
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfc_opt`，匹配`Invalid out buffer from kernel.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_jfc_opt
#### 4.25 URMA context、JFR对象无效导致获取JFR失败
* 故障编号：urma_434
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfr_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_jfr_opt
#### 4.26 URMA context、JFR对象无效导致获取JFR失败
* 故障编号：urma_435
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfr_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_jfr_opt
#### 4.27 获取ioctl的ioctl调用返回失败
* 故障编号：urma_436
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfr_opt`，匹配`ioctl failed in urma_cmd_get_jfr_opt, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交获取ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_get_jfr_opt
#### 4.28 URMA context无效导致获取JFR失败
* 故障编号：urma_437
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_jfr_opt`，匹配`Invalid out buffer from kernel.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFR，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_jfr_opt
#### 4.29 URMA context无效导致获取JFC失败
* 故障编号：urma_438
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_async_event`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_async_event
#### 4.30 URMA context无效导致获取ioctl失败
* 故障编号：urma_439
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_net_addr_list`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取ioctl，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_net_addr_list
#### 4.31 URMA context、sysfs设备信息无效导致查询设备失败
* 故障编号：urma_440
* 故障现象：
    * 关键日志：匹配`urma_cmd_query_device_attr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询设备，调用方传入的URMA context、sysfs设备信息不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_query_device_attr
#### 4.32 URMA context无效导致获取EID失败
* 故障编号：urma_441
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_eid_by_ip`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取EID，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_eid_by_ip
#### 4.33 URMA context无效导致获取EID失败
* 故障编号：urma_442
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_ip_by_eid`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取EID，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_ip_by_eid
#### 4.34 URMA context无效导致获取context失败
* 故障编号：urma_443
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_smac`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_smac
#### 4.35 URMA context无效导致获取context失败
* 故障编号：urma_444
* 故障现象：
    * 关键日志：匹配`urma_cmd_get_dmac`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_get_dmac
#### 4.36 执行get async event驱动命令的ioctl调用返回失败
* 故障编号：urma_445
* 故障现象：
    * 关键日志：匹配`urma_ioctl_get_async_event`，匹配`get async event ioctl failed, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交执行get async event驱动命令请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_ioctl_get_async_event
#### 4.37 获取JFC所需输入对象无效导致获取JFC失败
* 故障编号：urma_446
* 故障现象：
    * 关键日志：匹配`urma_get_jfc_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFC，调用方传入的获取JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_jfc_opt
#### 4.38 URMA context、provider操作表、provider未提供get_jfc_opt操作实现无效导致获取JFC失败
* 故障编号：urma_447
* 故障现象：
    * 关键日志：匹配`urma_get_jfc_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFC，调用方传入的URMA context、provider操作表、provider未提供get_jfc_opt操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_jfc_opt
#### 4.39 获取JFC过程中依赖步骤失败
* 故障编号：urma_448
* 故障现象：
    * 关键日志：匹配`urma_get_jfc_opt`，匹配`Failed to exec ops->get_jfc_opt.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_get_jfc_opt
#### 4.40 URMA context、provider操作表、JFS对象无效导致查询JFS失败
* 故障编号：urma_449
* 故障现象：
    * 关键日志：匹配`urma_query_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询JFS，调用方传入的URMA context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_query_jfs
#### 4.41 URMA context、provider操作表、JFS对象、provider未提供query_jfs操作实现无效导致查询JFS失败
* 故障编号：urma_450
* 故障现象：
    * 关键日志：匹配`urma_query_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询JFS，调用方传入的URMA context、provider操作表、JFS对象、provider未提供query_jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_query_jfs
#### 4.42 provider操作表、JFS对象无效导致获取JFS失败
* 故障编号：urma_451
* 故障现象：
    * 关键日志：匹配`urma_get_jfs_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFS，调用方传入的provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_jfs_opt
#### 4.43 URMA context、provider操作表、JFS对象、provider未提供get_jfs_opt操作实现无效导致获取JFS失败
* 故障编号：urma_452
* 故障现象：
    * 关键日志：匹配`urma_get_jfs_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFS，调用方传入的URMA context、provider操作表、JFS对象、provider未提供get_jfs_opt操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_jfs_opt
#### 4.44 获取JFS过程中依赖步骤失败
* 故障编号：urma_453
* 故障现象：
    * 关键日志：匹配`urma_get_jfs_opt`，匹配`Failed to exec ops->get_jfs_opt.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_get_jfs_opt
#### 4.45 URMA context、provider操作表、JFR对象无效导致查询JFR失败
* 故障编号：urma_454
* 故障现象：
    * 关键日志：匹配`urma_query_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询JFR，调用方传入的URMA context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_query_jfr
#### 4.46 URMA context、provider操作表、JFR对象、provider未提供query_jfr操作实现无效导致查询JFR失败
* 故障编号：urma_455
* 故障现象：
    * 关键日志：匹配`urma_query_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询JFR，调用方传入的URMA context、provider操作表、JFR对象、provider未提供query_jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_query_jfr
#### 4.47 provider操作表、JFR对象无效导致获取JFR失败
* 故障编号：urma_456
* 故障现象：
    * 关键日志：匹配`urma_get_jfr_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFR，调用方传入的provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_jfr_opt
#### 4.48 URMA context、provider操作表、JFR对象、provider未提供get_jfr_opt操作实现无效导致获取JFR失败
* 故障编号：urma_457
* 故障现象：
    * 关键日志：匹配`urma_get_jfr_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFR，调用方传入的URMA context、provider操作表、JFR对象、provider未提供get_jfr_opt操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_jfr_opt
#### 4.49 获取JFR过程中依赖步骤失败
* 故障编号：urma_458
* 故障现象：
    * 关键日志：匹配`urma_get_jfr_opt`，匹配`Failed to exec ops->get_jfr_opt.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_get_jfr_opt
#### 4.50 设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败
* 故障编号：urma_459
* 故障现象：
    * 关键日志：匹配`urma_check_seg_cfg`，匹配`Write access should be config with read access.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_check_seg_cfg
#### 4.51 设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败
* 故障编号：urma_460
* 故障现象：
    * 关键日志：匹配`urma_check_seg_cfg`，匹配`Atomic access should be config with read and write access.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_check_seg_cfg
#### 4.52 URMA context、provider操作表、JFS对象无效导致获取JFR失败
* 故障编号：urma_461
* 故障现象：
    * 关键日志：匹配`urma_get_async_event`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFR，调用方传入的URMA context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_async_event
#### 4.53 URMA context、provider操作表、provider未提供get_async_event操作实现无效导致获取context失败
* 故障编号：urma_462
* 故障现象：
    * 关键日志：匹配`urma_get_async_event`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取context，调用方传入的URMA context、provider操作表、provider未提供get_async_event操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_async_event
#### 4.54 URMA context、provider操作表无效导致获取EID失败
* 故障编号：urma_463
* 故障现象：
    * 关键日志：匹配`urma_get_eid_by_ip`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取EID，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_eid_by_ip
#### 4.55 URMA context、provider操作表、provider未提供get_eid_by_ip操作实现无效导致获取EID失败
* 故障编号：urma_464
* 故障现象：
    * 关键日志：匹配`urma_get_eid_by_ip`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取EID，调用方传入的URMA context、provider操作表、provider未提供get_eid_by_ip操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_eid_by_ip
#### 4.56 URMA context、provider操作表无效导致获取EID失败
* 故障编号：urma_465
* 故障现象：
    * 关键日志：匹配`urma_get_ip_by_eid`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取EID，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_ip_by_eid
#### 4.57 URMA context、provider操作表、provider未提供get_ip_by_eid操作实现无效导致获取EID失败
* 故障编号：urma_466
* 故障现象：
    * 关键日志：匹配`urma_get_ip_by_eid`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取EID，调用方传入的URMA context、provider操作表、provider未提供get_ip_by_eid操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_ip_by_eid
#### 4.58 URMA context、provider操作表无效导致获取context失败
* 故障编号：urma_467
* 故障现象：
    * 关键日志：匹配`urma_get_smac`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取context，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_smac
#### 4.59 URMA context、provider操作表、provider未提供get_smac操作实现无效导致获取context失败
* 故障编号：urma_468
* 故障现象：
    * 关键日志：匹配`urma_get_smac`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取context，调用方传入的URMA context、provider操作表、provider未提供get_smac操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_smac
#### 4.60 URMA context、provider操作表无效导致获取context失败
* 故障编号：urma_469
* 故障现象：
    * 关键日志：匹配`urma_get_dmac`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取context，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_dmac
#### 4.61 URMA context、provider操作表、provider未提供get_dmac操作实现无效导致获取context失败
* 故障编号：urma_470
* 故障现象：
    * 关键日志：匹配`urma_get_dmac`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取context，调用方传入的URMA context、provider操作表、provider未提供get_dmac操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_dmac
#### 4.62 读取sysfs过程中依赖步骤失败
* 故障编号：urma_471
* 故障现象：
    * 关键日志：匹配`urma_read_sysfs_file`，匹配`snprintf failed`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于读取sysfs，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_read_sysfs_file
#### 4.63 设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败
* 故障编号：urma_472
* 故障现象：
    * 关键日志：匹配`urma_read_sysfs_file`，匹配`Failed open file:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_read_sysfs_file
#### 4.64 设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败
* 故障编号：urma_473
* 故障现象：
    * 关键日志：匹配`urma_read_sysfs_file`，匹配`Failed read file:`，匹配`, ret:`，匹配`d, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_read_sysfs_file
#### 4.65 读取EID过程中依赖步骤失败
* 故障编号：urma_474
* 故障现象：
    * 关键日志：匹配`read_eid_list_sysyf`，匹配`printf failed, eid idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于读取EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：read_eid_list_sysyf
#### 4.66 EID信息的sysfs读取或解析失败
* 故障编号：urma_475
* 故障现象：
    * 关键日志：匹配`read_eid_list_sysyf`，匹配`Failed to read sysfs file`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取EID信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：read_eid_list_sysyf
#### 4.67 读取EID过程中依赖步骤失败
* 故障编号：urma_476
* 故障现象：
    * 关键日志：匹配`read_eid_sysfs_with_index`，匹配`snprintf failed, eid idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于读取EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：read_eid_sysfs_with_index
#### 4.68 EID信息的sysfs读取或解析失败
* 故障编号：urma_477
* 故障现象：
    * 关键日志：匹配`read_eid_sysfs_with_index`，匹配`Failed to read sysfs file`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取EID信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：read_eid_sysfs_with_index
#### 4.69 EID信息的sysfs读取或解析失败
* 故障编号：urma_478
* 故障现象：
    * 关键日志：匹配`read_eid_sysfs_with_index`，匹配`Failed to parse eid value, dev name:`，匹配`, eid idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取EID信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：read_eid_sysfs_with_index
#### 4.70 EID信息的sysfs读取或解析失败
* 故障编号：urma_479
* 故障现象：
    * 关键日志：匹配`urma_ioctl_get_eid_list`，匹配`Failed to open urma cdev with path`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取EID信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_ioctl_get_eid_list
#### 4.71 EID信息的sysfs读取或解析失败
* 故障编号：urma_480
* 故障现象：
    * 关键日志：匹配`urma_query_device_attr`，匹配`Failed to get cdev_path, dev_name:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取EID信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_query_device_attr
#### 4.72 字符设备路径信息的sysfs读取或解析失败
* 故障编号：urma_481
* 故障现象：
    * 关键日志：匹配`urma_query_device_attr`，匹配`Failed to open urma cdev, path`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_query_device_attr
#### 4.73 解析端口过程中依赖步骤失败
* 故障编号：urma_482
* 故障现象：
    * 关键日志：匹配`urma_parse_port_attr`，匹配`snprintf failed, path:`，匹配`, port_num:`，匹配`hu.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解析端口，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_parse_port_attr
#### 4.74 执行设备过程中依赖步骤失败
* 故障编号：urma_483
* 故障现象：
    * 关键日志：匹配`urma_discover_sysfs_path`，匹配`snprintf failed, dev_name:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_discover_sysfs_path
#### 4.75 设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败
* 故障编号：urma_484
* 故障现象：
    * 关键日志：匹配`urma_scan_sysfs_devices`，匹配`open failed, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_scan_sysfs_devices
#### 4.76 释放sysfs过程中依赖步骤失败
* 故障编号：urma_485
* 故障现象：
    * 关键日志：匹配`urma_scan_sysfs_devices`，匹配`Failed close dir:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放sysfs，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_scan_sysfs_devices
#### 4.77 JFS对象、WR对象无效导致读取JFS失败
* 故障编号：urma_486
* 故障现象：
    * 关键日志：匹配`urma_read`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于读取JFS，调用方传入的JFS对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_read
#### 4.78 设置线程所需输入对象无效导致设置线程失败
* 故障编号：urma_487
* 故障现象：
    * 关键日志：匹配`urma_log_set_thread_tag`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置线程，调用方传入的设置线程所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_log_set_thread_tag
#### 4.79 获取URMA资源过程中依赖步骤失败
* 故障编号：urma_488
* 故障现象：
    * 关键日志：匹配`urma_open_drivers`，匹配`Failed to get dl addr:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_open_drivers
#### 4.80 设备对象、sysfs设备信息无效导致查询设备失败
* 故障编号：urma_489
* 故障现象：
    * 关键日志：匹配`urma_query_device`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询设备，调用方传入的设备对象、sysfs设备信息不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_query_device
#### 4.81 查询设备过程中依赖步骤失败
* 故障编号：urma_490
* 故障现象：
    * 关键日志：匹配`urma_query_device`，匹配`Failed to query device attr, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_query_device
#### 4.82 设备对象、sysfs设备信息无效导致查询设备失败
* 故障编号：urma_491
* 故障现象：
    * 关键日志：匹配`urma_query_device`，匹配`Invalid dev_name.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询设备，调用方传入的设备对象、sysfs设备信息不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_query_device
#### 4.83 获取设备过程中依赖步骤失败
* 故障编号：urma_492
* 故障现象：
    * 关键日志：匹配`urma_query_device`，匹配`urma get device list failed, device_num:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_query_device
#### 4.84 查询设备过程中依赖步骤失败
* 故障编号：urma_493
* 故障现象：
    * 关键日志：匹配`urma_query_device`，匹配`device list name:`，匹配`does not match dev_name:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_query_device
#### 4.85 获取设备过程中依赖步骤失败
* 故障编号：urma_494
* 故障现象：
    * 关键日志：匹配`urma_query_device`，匹配`urma get device list failed!`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_query_device
#### 4.86 设备对象、sysfs设备信息、provider操作表无效导致查询设备失败
* 故障编号：urma_495
* 故障现象：
    * 关键日志：匹配`urma_query_eid`，匹配`Invalid parameter with err dev or ops.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询设备，调用方传入的设备对象、sysfs设备信息、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_query_eid
#### 4.87 查询EID过程中依赖步骤失败
* 故障编号：urma_496
* 故障现象：
    * 关键日志：匹配`urma_query_eid`，匹配`Failed to query eid.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于查询EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_query_eid
#### 4.88 EID信息的sysfs读取或解析失败
* 故障编号：urma_497
* 故障现象：
    * 关键日志：匹配`urma_query_eid`，匹配`Failed to open urma cdev with path`，匹配`, dev_fd:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取EID信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_query_eid
#### 4.89 URMA context无效导致获取context失败
* 故障编号：urma_498
* 故障现象：
    * 关键日志：匹配`urma_get_uasid`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_uasid
#### 4.90 执行线程所需输入对象无效导致初始化线程失败
* 故障编号：urma_499
* 故障现象：
    * 关键日志：匹配`urma_perf_thread_exit_cleanup`，匹配`Urma perf thread cleanup, thread index`，匹配`is invalid.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于初始化线程，调用方传入的执行线程所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_perf_thread_exit_cleanup
#### 4.91 获取URMA资源所需输入对象无效导致获取锁失败
* 故障编号：urma_500
* 故障现象：
    * 关键日志：匹配`urma_get_perf_info`，匹配`Urma perf info get failed, perf_buf or length is invalid`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取锁，调用方传入的获取URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_get_perf_info
#### 4.92 获取锁过程中依赖步骤失败
* 故障编号：urma_501
* 故障现象：
    * 关键日志：匹配`urma_get_perf_info`，匹配`Urma perf get info failed, need`，匹配`bytes buffer, but only`，匹配`provided`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取锁，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_get_perf_info

## 5 资源导入/注册失败
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 5.1 物理 JFR导入时下层资源准备失败
* 故障编号：urma_502
* 故障现象：
    * 关键日志：匹配`bondp_import_pjfr`，匹配`Failed to import tjfr`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责导入物理 JFR，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_import_pjfr
#### 5.2 JFR导入时下层资源准备失败
* 故障编号：urma_503
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pjfr`，匹配`RM jfr import requires drv_ext.vjfs`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责导入JFR，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_unimport_pjfr
#### 5.3 健康检查导入时下层资源准备失败
* 故障编号：urma_504
* 故障现象：
    * 关键日志：匹配`import_check_tseg_by_import_result`，匹配`Failed to import health check seg (`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责导入健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：import_check_tseg_by_import_result
#### 5.4 健康检查清理阶段下层释放操作失败
* 故障编号：urma_505
* 故障现象：
    * 关键日志：匹配`bondp_unimport_health_check_tseg`，匹配`Failed to unimport health check seg (`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销健康检查相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_unimport_health_check_tseg
#### 5.5 Segment清理阶段下层释放操作失败
* 故障编号：urma_506
* 故障现象：
    * 关键日志：匹配`bondp_delete_pseg`，匹配`Failed to unregister pseg`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Segment相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_pseg
#### 5.6 Segment对象无效导致创建Segment失败
* 故障编号：urma_507
* 故障现象：
    * 关键日志：匹配`bondp_create_pseg`，匹配`Invalid segment address for bondp seg`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建Segment，调用方传入的Segment对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_create_pseg
#### 5.7 Segment注册时下层资源准备失败
* 故障编号：urma_508
* 故障现象：
    * 关键日志：匹配`bondp_create_pseg`，匹配`Failed to register pseg`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责注册Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_pseg
#### 5.8 Segment清理阶段下层释放操作失败
* 故障编号：urma_509
* 故障现象：
    * 关键日志：匹配`bondp_delete_vseg`，匹配`Failed to unregister segment, token_id:`，匹配`, handle:`，匹配`u.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Segment相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_vseg
#### 5.9 Segment注册时下层资源准备失败
* 故障编号：urma_510
* 故障现象：
    * 关键日志：匹配`bondp_create_vseg`，匹配`Fail to register vseg, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责注册Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_vseg
#### 5.10 URMA context、Segment对象无效导致注册Token失败
* 故障编号：urma_511
* 故障现象：
    * 关键日志：匹配`bondp_create_vseg`，匹配`Invalid token id for register bondp seg`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于注册Token，调用方传入的URMA context、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_create_vseg
#### 5.11 Segment相关临时结构或命令参数分配失败
* 故障编号：urma_512
* 故障现象：
    * 关键日志：匹配`bondp_create_vseg`，匹配`Failed to alloc bondp segment comp`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配Segment前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：bondp_create_vseg
#### 5.12 Segment创建时下层资源准备失败
* 故障编号：urma_513
* 故障现象：
    * 关键日志：匹配`bondp_create_vseg`，匹配`Failed to create pseg`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_vseg
#### 5.13 Segment创建时下层资源准备失败
* 故障编号：urma_514
* 故障现象：
    * 关键日志：匹配`bondp_create_vseg`，匹配`Failed to create vseg`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责创建Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_create_vseg
#### 5.14 Token清理阶段下层释放操作失败
* 故障编号：urma_515
* 故障现象：
    * 关键日志：匹配`bondp_unregister_seg_inner`，匹配`Failed to delete vseg, token_id:`，匹配`, handle:`，匹配`u.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Token相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_unregister_seg_inner
#### 5.15 Token清理阶段下层释放操作失败
* 故障编号：urma_516
* 故障现象：
    * 关键日志：匹配`bondp_unregister_seg_inner`，匹配`Failed to delete pseg for vseg, token_id:`，匹配`, handle:`，匹配`u.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Token相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_unregister_seg_inner
#### 5.16 Segment导入时下层资源准备失败
* 故障编号：urma_517
* 故障现象：
    * 关键日志：匹配`import_pseg`，匹配`Failed to import seg (`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责导入Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：import_pseg
#### 5.17 Segment相关临时结构或命令参数分配失败
* 故障编号：urma_518
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pseg`，匹配`Failed to alloc target seg`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数在分配Segment前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。
* 解决办法：无
* 函数名：bondp_unimport_pseg
#### 5.18 解除导入Token过程中依赖步骤失败
* 故障编号：urma_519
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pseg`，匹配`Failed to lookup v2p_token_id, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入Token，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_unimport_pseg
#### 5.19 Token导入时下层资源准备失败
* 故障编号：urma_520
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pseg`，匹配`Failed to import vseg`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责导入Token，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_unimport_pseg
#### 5.20 Segment导入时下层资源准备失败
* 故障编号：urma_521
* 故障现象：
    * 关键日志：匹配`bondp_unimport_pseg`，匹配`Failed to import pseg`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责导入Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：bondp_unimport_pseg
#### 5.21 URMA context无效导致注册Segment失败
* 故障编号：urma_522
* 故障现象：
    * 关键日志：匹配`urma_cmd_register_seg`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于注册Segment，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_register_seg
#### 5.22 注册ioctl的ioctl调用返回失败
* 故障编号：urma_523
* 故障现象：
    * 关键日志：匹配`urma_cmd_register_seg`，匹配`ioctl failed in urma_cmd_register_seg, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交注册ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_register_seg
#### 5.23 URMA context无效导致注销Segment失败
* 故障编号：urma_524
* 故障现象：
    * 关键日志：匹配`urma_cmd_unregister_seg`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于注销Segment，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_unregister_seg
#### 5.24 注销ioctl的ioctl调用返回失败
* 故障编号：urma_525
* 故障现象：
    * 关键日志：匹配`urma_cmd_unregister_seg`，匹配`ioctl failed, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交注销ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_unregister_seg
#### 5.25 URMA context、Segment对象无效导致导入Segment失败
* 故障编号：urma_526
* 故障现象：
    * 关键日志：匹配`urma_cmd_import_seg`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于导入Segment，调用方传入的URMA context、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_import_seg
#### 5.26 URMA context无效导致解除导入Segment失败
* 故障编号：urma_527
* 故障现象：
    * 关键日志：匹配`urma_cmd_unimport_seg`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入Segment，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_unimport_seg
#### 5.27 URMA context、设备对象、provider操作表、Segment对象无效导致解除导入Segment失败
* 故障编号：urma_528
* 故障现象：
    * 关键日志：匹配`urma_unimport_seg`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入Segment，调用方传入的URMA context、设备对象、provider操作表、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unimport_seg
#### 5.28 URMA context、provider操作表、provider未提供unimport_seg操作实现无效导致解除导入Segment失败
* 故障编号：urma_529
* 故障现象：
    * 关键日志：匹配`urma_unimport_seg`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入Segment，调用方传入的URMA context、provider操作表、provider未提供unimport_seg操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unimport_seg
#### 5.29 URMA context、provider操作表无效导致解除导入Segment失败
* 故障编号：urma_530
* 故障现象：
    * 关键日志：匹配`urma_unimport_seg`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入Segment，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unimport_seg
#### 5.30 URMA context、provider操作表、provider未提供alloc_token_id操作实现无效导致解除导入Segment失败
* 故障编号：urma_531
* 故障现象：
    * 关键日志：匹配`urma_unimport_seg`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入Segment，调用方传入的URMA context、provider操作表、provider未提供alloc_token_id操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unimport_seg
#### 5.31 Segment注册时下层资源准备失败
* 故障编号：urma_532
* 故障现象：
    * 关键日志：匹配`urma_unimport_seg`，匹配`[DRV_ERR]Failed to register seg, dev_name:`，匹配`, eid_idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责注册Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：urma_unimport_seg
#### 5.32 URMA context、设备对象、Segment对象无效导致解除导入Segment失败
* 故障编号：urma_533
* 故障现象：
    * 关键日志：匹配`urma_unimport_seg`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入Segment，调用方传入的URMA context、设备对象、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unimport_seg
#### 5.33 URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_token_id_ex操作实现无效导致解除导入Segment失败
* 故障编号：urma_534
* 故障现象：
    * 关键日志：匹配`urma_unimport_seg`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入Segment，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_token_id_ex操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unimport_seg
#### 5.34 解除导入设备过程中依赖步骤失败
* 故障编号：urma_535
* 故障现象：
    * 关键日志：匹配`urma_unimport_seg`，匹配`dev not support token id table mode.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于解除导入设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_unimport_seg
#### 5.35 设置Token过程中依赖步骤失败
* 故障编号：urma_536
* 故障现象：
    * 关键日志：匹配`urma_check_seg_cfg`，匹配`token_id must set when token_id_valid is true, or must NULL when token_id_valid is false.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Token，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_check_seg_cfg
#### 5.36 Segment注册时下层资源准备失败
* 故障编号：urma_537
* 故障现象：
    * 关键日志：匹配`urma_check_seg_cfg`，匹配`[DRV_ERR]register seg failed, dev_name:`，匹配`, eid_idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责注册Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。
* 解决办法：无
* 函数名：urma_check_seg_cfg
#### 5.37 URMA context、设备对象、Segment对象无效导致注销Segment失败
* 故障编号：urma_538
* 故障现象：
    * 关键日志：匹配`urma_unregister_seg`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于注销Segment，调用方传入的URMA context、设备对象、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unregister_seg
#### 5.38 URMA context、设备对象、provider操作表、Segment对象、provider未提供unregister_seg操作实现无效导致注销Segment失败
* 故障编号：urma_539
* 故障现象：
    * 关键日志：匹配`urma_unregister_seg`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于注销Segment，调用方传入的URMA context、设备对象、provider操作表、Segment对象、provider未提供unregister_seg操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unregister_seg
#### 5.39 Segment清理阶段下层释放操作失败
* 故障编号：urma_540
* 故障现象：
    * 关键日志：匹配`urma_unregister_seg`，匹配`[DRV_ERR]Unregister seg fail, dev_name:`，匹配`, eid_idx:`，匹配`, tid:`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Segment相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_unregister_seg

## 6 数据收发失败
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 6.1 epoll数据通路处理失败
* 故障编号：urma_541
* 故障现象：
    * 关键日志：匹配`bondp_wait_jfc`，匹配`Epoll wait err, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_wait_jfc
#### 6.2 JFS对象、WR对象无效导致投递JFS失败
* 故障编号：urma_542
* 故障现象：
    * 关键日志：匹配`comp_post_send`，匹配`Invalid post jfs wr type:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于投递JFS，调用方传入的JFS对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：comp_post_send
#### 6.3 JFR对象、WR对象无效导致投递JFR失败
* 故障编号：urma_543
* 故障现象：
    * 关键日志：匹配`comp_post_recv`，匹配`Invalid post jfr wr type:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于投递JFR，调用方传入的JFR对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：comp_post_recv
#### 6.4 WR数据通路处理失败
* 故障编号：urma_544
* 故障现象：
    * 关键日志：匹配`post_send_check_jfs_wr_valid`，匹配`when set write_wr, either of src/dst num_sge/sge has been set zero or NULL.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：post_send_check_jfs_wr_valid
#### 6.5 WR数据通路处理失败
* 故障编号：urma_545
* 故障现象：
    * 关键日志：匹配`post_send_check_jfs_wr_valid`，匹配`when set cas_wr, either src or dst is NULL.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：post_send_check_jfs_wr_valid
#### 6.6 WR数据通路处理失败
* 故障编号：urma_546
* 故障现象：
    * 关键日志：匹配`post_send_check_jfs_wr_valid`，匹配`when set faa_wr, either src or dst is NULL.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：post_send_check_jfs_wr_valid
#### 6.7 WR对象无效导致投递组件失败
* 故障编号：urma_547
* 故障现象：
    * 关键日志：匹配`post_send_check_valid`，匹配`Try to call post_send api by invalid comp_type:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于投递组件，调用方传入的WR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：post_send_check_valid
#### 6.8 WR对象无效导致投递组件失败
* 故障编号：urma_548
* 故障现象：
    * 关键日志：匹配`post_send_check_valid`，匹配`Invalid src_chip_id:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于投递组件，调用方传入的WR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：post_send_check_valid
#### 6.9 WR数据通路处理失败
* 故障编号：urma_549
* 故障现象：
    * 关键日志：匹配`bondp_post_send_wr_no_store`，匹配`Bondp supports at most`，匹配`wr_list.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_post_send_wr_no_store
#### 6.10 JFS数据通路处理失败
* 故障编号：urma_550
* 故障现象：
    * 关键日志：匹配`bondp_post_send_wr_and_store`，匹配`Failed to copy jfs wr`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_post_send_wr_and_store
#### 6.11 JFS数据通路处理失败
* 故障编号：urma_551
* 故障现象：
    * 关键日志：匹配`bondp_post_send_wr_and_store`，匹配`Failed to convert jfs wr`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_post_send_wr_and_store
#### 6.12 WR数据通路处理失败
* 故障编号：urma_552
* 故障现象：
    * 关键日志：匹配`bondp_post_send_wr_and_store`，匹配`Failed to post send wr`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_post_send_wr_and_store
#### 6.13 WR数据通路处理失败
* 故障编号：urma_553
* 故障现象：
    * 关键日志：匹配`bondp_post_recv_wr_no_store`，匹配`Bondp supports at most`，匹配`wr_list.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_post_recv_wr_no_store
#### 6.14 JFR数据通路处理失败
* 故障编号：urma_554
* 故障现象：
    * 关键日志：匹配`bondp_post_recv_wr_and_store`，匹配`Failed to copy jfr wr`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_post_recv_wr_and_store
#### 6.15 JFR数据通路处理失败
* 故障编号：urma_555
* 故障现象：
    * 关键日志：匹配`bondp_post_recv_wr_and_store`，匹配`Failed to convert jfr wr`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_post_recv_wr_and_store
#### 6.16 WR数据通路处理失败
* 故障编号：urma_556
* 故障现象：
    * 关键日志：匹配`bondp_post_recv_wr_and_store`，匹配`Failed to post recv wr`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_post_recv_wr_and_store
#### 6.17 设备对象、sysfs设备信息、WR对象无效导致投递组件失败
* 故障编号：urma_557
* 故障现象：
    * 关键日志：匹配`post_recv_check_wr_list_valid`，匹配`Invalid bdp_recv_comp type:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于投递组件，调用方传入的设备对象、sysfs设备信息、WR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：post_recv_check_wr_list_valid
#### 6.18 执行URMA资源所需输入对象无效导致刷出虚拟 Jetty失败
* 故障编号：urma_558
* 故障现象：
    * 关键日志：匹配`handle_fake_cr_with_store`，匹配`Invalid cr error status:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于刷出虚拟 Jetty，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：handle_fake_cr_with_store
#### 6.19 JFS数据通路处理失败
* 故障编号：urma_559
* 故障现象：
    * 关键日志：匹配`handle_send_cr_with_store`，匹配`Failed to resend jfs wr, wr_id:`，匹配`u`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：handle_send_cr_with_store
#### 6.20 JFS数据通路处理失败
* 故障编号：urma_560
* 故障现象：
    * 关键日志：匹配`convert_jfs_vwr_to_pwr`，匹配`Unsupported send opcode`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：convert_jfs_vwr_to_pwr
#### 6.21 执行URMA资源所需输入对象无效导致激活组件失败
* 故障编号：urma_561
* 故障现象：
    * 关键日志：匹配`schedule_send_balance`，匹配`Invalid min_active_count.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活组件，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：schedule_send_balance
#### 6.22 激活设备过程中依赖步骤失败
* 故障编号：urma_562
* 故障现象：
    * 关键日志：匹配`schedule_send_balance`，匹配`Unsupported bonding level:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：schedule_send_balance
#### 6.23 激活端口过程中依赖步骤失败
* 故障编号：urma_563
* 故障现象：
    * 关键日志：匹配`schedule_send`，匹配`No active port`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活端口，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：schedule_send
#### 6.24 激活端口过程中依赖步骤失败
* 故障编号：urma_564
* 故障现象：
    * 关键日志：匹配`schedule_recv`，匹配`No active port`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活端口，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：schedule_recv
#### 6.25 健康检查数据通路处理失败
* 故障编号：urma_565
* 故障现象：
    * 关键日志：匹配`bondp_health_calc_primary_interval_us`，匹配`Health check epoll_wait failed, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：bondp_health_calc_primary_interval_us
#### 6.26 JFC数据通路处理失败
* 故障编号：urma_566
* 故障现象：
    * 关键日志：匹配`urma_active_jfc`，匹配`Jfc state is wrong in active_jfc.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：urma_active_jfc
#### 6.27 JFC数据通路处理失败
* 故障编号：urma_567
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfc`，匹配`Jfc state is wrong in deactive_jfc.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：urma_deactive_jfc
#### 6.28 URMA context、JFS对象无效导致刷出JFS失败
* 故障编号：urma_568
* 故障现象：
    * 关键日志：匹配`urma_flush_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于刷出JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_flush_jfs
#### 6.29 URMA context、provider操作表、JFS对象、provider未提供flush_jfs操作实现无效导致刷出JFS失败
* 故障编号：urma_569
* 故障现象：
    * 关键日志：匹配`urma_flush_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于刷出JFS，调用方传入的URMA context、provider操作表、JFS对象、provider未提供flush_jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_flush_jfs
#### 6.30 JFS数据通路处理失败
* 故障编号：urma_570
* 故障现象：
    * 关键日志：匹配`urma_active_jfs`，匹配`jfs or jfc state is wrong in active_jfs.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：urma_active_jfs
#### 6.31 JFS数据通路处理失败
* 故障编号：urma_571
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfs`，匹配`jfs state is wrong in deactive_jfs.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：urma_deactive_jfs
#### 6.32 JFR数据通路处理失败
* 故障编号：urma_572
* 故障现象：
    * 关键日志：匹配`urma_active_jfr`，匹配`jfr or jfc state is wrong in active_jfr.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：urma_active_jfr
#### 6.33 JFR数据通路处理失败
* 故障编号：urma_573
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfr`，匹配`jfr state is wrong in deactive_jfr.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路中断。
* 解决办法：无
* 函数名：urma_deactive_jfr
#### 6.34 JFR对象、WR对象无效导致执行JFR失败
* 故障编号：urma_574
* 故障现象：
    * 关键日志：匹配`check_valid_jfr_wr`，匹配`There are invalid parameters.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行JFR，调用方传入的JFR对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：check_valid_jfr_wr
#### 6.35 JFS对象无效导致获取JFS失败
* 故障编号：urma_575
* 故障现象：
    * 关键日志：匹配`urma_write`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFS，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_write
#### 6.36 投递WR过程中依赖步骤失败
* 故障编号：urma_576
* 故障现象：
    * 关键日志：匹配`urma_send`，匹配`null pointer exists in tjfr.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于投递WR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_send
#### 6.37 JFS对象无效导致获取JFS失败
* 故障编号：urma_577
* 故障现象：
    * 关键日志：匹配`urma_send`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFS，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_send
#### 6.38 JFS对象无效导致获取JFR失败
* 故障编号：urma_578
* 故障现象：
    * 关键日志：匹配`urma_send`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取JFR，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_send
#### 6.39 JFS对象、JFR对象、WR对象无效导致投递WR失败
* 故障编号：urma_579
* 故障现象：
    * 关键日志：匹配`urma_recv`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于投递WR，调用方传入的JFS对象、JFR对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_recv
#### 6.40 JFR对象、WR对象无效导致投递JFR失败
* 故障编号：urma_580
* 故障现象：
    * 关键日志：匹配`urma_recv`，匹配`There are invalid parameters.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于投递JFR，调用方传入的JFR对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_recv
#### 6.41 JFR对象、WR对象无效导致轮询JFC失败
* 故障编号：urma_581
* 故障现象：
    * 关键日志：匹配`urma_poll_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于轮询JFC，调用方传入的JFR对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_poll_jfc
#### 6.42 JFS对象、WR对象无效导致投递JFS失败
* 故障编号：urma_582
* 故障现象：
    * 关键日志：匹配`urma_post_jfs_wr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于投递JFS，调用方传入的JFS对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_post_jfs_wr
#### 6.43 JFR对象、WR对象无效导致投递JFR失败
* 故障编号：urma_583
* 故障现象：
    * 关键日志：匹配`urma_post_jfr_wr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于投递JFR，调用方传入的JFR对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_post_jfr_wr
#### 6.44 获取URMA资源过程中依赖步骤失败
* 故障编号：urma_584
* 故障现象：
    * 关键日志：匹配`urma_config_perf_attr`，匹配`Urma perf config failed. perf record is not started.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_config_perf_attr
#### 6.45 执行URMA资源所需输入对象无效导致执行URMA资源失败
* 故障编号：urma_585
* 故障现象：
    * 关键日志：匹配`urma_config_perf_attr`，匹配`Urma perf config failed. perf_attr is invalid.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行URMA资源，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_config_perf_attr
#### 6.46 执行URMA资源所需输入对象无效导致执行context失败
* 故障编号：urma_586
* 故障现象：
    * 关键日志：匹配`urma_step_perf`，匹配`Urma perf type`，匹配`is invalid.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行context，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_step_perf

## 7 资源销毁/清理失败
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 7.1 JFCE清理阶段下层释放操作失败
* 故障编号：urma_587
* 故障现象：
    * 关键日志：匹配`bondp_delete_pjfce`，匹配`Failed to delete pjfce`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFCE相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_pjfce
#### 7.2 JFCE清理阶段下层释放操作失败
* 故障编号：urma_588
* 故障现象：
    * 关键日志：匹配`bondp_delete_jfce`，匹配`Failed to delete jfce[`，匹配`], still in use. use_cnt:`，匹配`u`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFCE相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jfce
#### 7.3 JFCE清理阶段下层释放操作失败
* 故障编号：urma_589
* 故障现象：
    * 关键日志：匹配`bondp_delete_jfce`，匹配`Failed to delete pjfce.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFCE相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jfce
#### 7.4 JFCE清理阶段下层释放操作失败
* 故障编号：urma_590
* 故障现象：
    * 关键日志：匹配`bondp_delete_jfce`，匹配`Failed to delete vjfce.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFCE相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jfce
#### 7.5 物理 JFC清理阶段下层释放操作失败
* 故障编号：urma_591
* 故障现象：
    * 关键日志：匹配`bondp_delete_pjfc`，匹配`Failed to delete pjfc`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销物理 JFC相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_pjfc
#### 7.6 JFC清理阶段下层释放操作失败
* 故障编号：urma_592
* 故障现象：
    * 关键日志：匹配`bondp_delete_jfc`，匹配`Failed to delete jfc[`，匹配`], still in use. use_cnt:`，匹配`u`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFC相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jfc
#### 7.7 虚拟 JFC清理阶段下层释放操作失败
* 故障编号：urma_593
* 故障现象：
    * 关键日志：匹配`bondp_delete_jfc`，匹配`Failed to delete vjfc`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销虚拟 JFC相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jfc
#### 7.8 物理 JFC清理阶段下层释放操作失败
* 故障编号：urma_594
* 故障现象：
    * 关键日志：匹配`bondp_delete_jfc`，匹配`Failed to delete pjfc`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销物理 JFC相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jfc
#### 7.9 物理 JFS清理阶段下层释放操作失败
* 故障编号：urma_595
* 故障现象：
    * 关键日志：匹配`bondp_delete_pjfs`，匹配`Failed to delete pjfs`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销物理 JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_pjfs
#### 7.10 JFS清理阶段下层释放操作失败
* 故障编号：urma_596
* 故障现象：
    * 关键日志：匹配`bondp_delete_jfs`，匹配`Failed to delete jfs[`，匹配`], still in use. use_cnt:`，匹配`u`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jfs
#### 7.11 虚拟 JFS清理阶段下层释放操作失败
* 故障编号：urma_597
* 故障现象：
    * 关键日志：匹配`bondp_delete_jfs`，匹配`Failed to delete vjfs`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销虚拟 JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jfs
#### 7.12 物理 JFS清理阶段下层释放操作失败
* 故障编号：urma_598
* 故障现象：
    * 关键日志：匹配`bondp_delete_jfs`，匹配`Failed to delete pjfs`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销物理 JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jfs
#### 7.13 物理 JFR清理阶段下层释放操作失败
* 故障编号：urma_599
* 故障现象：
    * 关键日志：匹配`bondp_delete_pjfr`，匹配`Failed to delete pjfr`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销物理 JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_pjfr
#### 7.14 JFR清理阶段下层释放操作失败
* 故障编号：urma_600
* 故障现象：
    * 关键日志：匹配`bondp_delete_jfr`，匹配`Failed to delete jfr[`，匹配`], still in use. use_cnt:`，匹配`u`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jfr
#### 7.15 虚拟 JFR清理阶段下层释放操作失败
* 故障编号：urma_601
* 故障现象：
    * 关键日志：匹配`bondp_delete_jfr`，匹配`Failed to delete_vjfr`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销虚拟 JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jfr
#### 7.16 物理 JFR清理阶段下层释放操作失败
* 故障编号：urma_602
* 故障现象：
    * 关键日志：匹配`bondp_delete_jfr`，匹配`Failed to delete pjfr`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销物理 JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_jfr
#### 7.17 context清理阶段下层释放操作失败
* 故障编号：urma_603
* 故障现象：
    * 关键日志：匹配`bondp_delete_vcontext`，匹配`Failed to urma_cmd_delete_context`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销context相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_vcontext
#### 7.18 设备清理阶段下层释放操作失败
* 故障编号：urma_604
* 故障现象：
    * 关键日志：匹配`bondp_delete_pcontext`，匹配`Failed to delete pctx, idx:`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销设备相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_pcontext
#### 7.19 context清理阶段下层释放操作失败
* 故障编号：urma_605
* 故障现象：
    * 关键日志：匹配`bondp_delete_context`，匹配`Failed to delete pcontext`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销context相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_context
#### 7.20 context清理阶段下层释放操作失败
* 故障编号：urma_606
* 故障现象：
    * 关键日志：匹配`bondp_delete_context`，匹配`Failed to delete vcontext`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销context相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_delete_context
#### 7.21 锁清理阶段下层释放操作失败
* 故障编号：urma_607
* 故障现象：
    * 关键日志：匹配`bondp_set_bonding_mode`，匹配`Failed to delete pctx when set bonding mode, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销锁相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：bondp_set_bonding_mode
#### 7.22 删除URMA资源所需输入对象无效导致删除Segment失败
* 故障编号：urma_608
* 故障现象：
    * 关键日志：匹配`bondp_delete_vseg`，匹配`invalid param.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Segment，调用方传入的删除URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_delete_vseg
#### 7.23 URMA context无效导致删除context失败
* 故障编号：urma_609
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_context`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_context
#### 7.24 URMA context、JFS对象无效导致删除JFS失败
* 故障编号：urma_610
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfs`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jfs
#### 7.25 删除ioctl的ioctl调用返回失败
* 故障编号：urma_611
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfs`，匹配`ioctl failed, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交删除ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_delete_jfs
#### 7.26 JFS对象无效导致删除JFS失败
* 故障编号：urma_612
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfs_batch`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFS，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jfs_batch
#### 7.27 URMA context、JFS对象无效导致删除JFS失败
* 故障编号：urma_613
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfs_batch`，匹配`Invalid parameter, index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jfs_batch
#### 7.28 URMA context、JFS对象无效导致删除JFS失败
* 故障编号：urma_614
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfs_batch`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jfs_batch
#### 7.29 JFS清理阶段下层释放操作失败
* 故障编号：urma_615
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfs_batch`，匹配`jfs not from the same dev, cannot delete in a batch, index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_cmd_delete_jfs_batch
#### 7.30 删除ioctl的ioctl调用返回失败
* 故障编号：urma_616
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfs_batch`，匹配`ioctl failed in urma_cmd_delete_jfs_batch , ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交删除ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_delete_jfs_batch
#### 7.31 删除JFS过程中依赖步骤失败
* 故障编号：urma_617
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfs_batch`，匹配`bad jfs index exceed array length, bad_jfs_index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_delete_jfs_batch
#### 7.32 URMA context、JFS对象无效导致释放JFS失败
* 故障编号：urma_618
* 故障现象：
    * 关键日志：匹配`urma_cmd_free_jfs`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_free_jfs
#### 7.33 释放ioctl的ioctl调用返回失败
* 故障编号：urma_619
* 故障现象：
    * 关键日志：匹配`urma_cmd_free_jfs`，匹配`ioctl failed in urma_cmd_free_jfs , ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交释放ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_free_jfs
#### 7.34 URMA context、JFR对象无效导致删除JFR失败
* 故障编号：urma_620
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfr`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jfr
#### 7.35 删除ioctl的ioctl调用返回失败
* 故障编号：urma_621
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfr`，匹配`ioctl failed in urma_cmd_delete_jfr, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交删除ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_delete_jfr
#### 7.36 JFR对象无效导致删除JFR失败
* 故障编号：urma_622
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfr_batch`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFR，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jfr_batch
#### 7.37 URMA context、JFR对象无效导致删除JFR失败
* 故障编号：urma_623
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfr_batch`，匹配`Invalid parameter, index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jfr_batch
#### 7.38 URMA context、JFR对象无效导致删除JFR失败
* 故障编号：urma_624
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfr_batch`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jfr_batch
#### 7.39 JFR清理阶段下层释放操作失败
* 故障编号：urma_625
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfr_batch`，匹配`jfr not from the same dev, cannot delete in a batch, index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_cmd_delete_jfr_batch
#### 7.40 删除ioctl的ioctl调用返回失败
* 故障编号：urma_626
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfr_batch`，匹配`ioctl failed in urma_cmd_delete_jfr_batch , ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交删除ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_delete_jfr_batch
#### 7.41 删除JFR过程中依赖步骤失败
* 故障编号：urma_627
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfr_batch`，匹配`bad jfr index exceed array length, bad_jfr_index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_delete_jfr_batch
#### 7.42 URMA context无效导致删除JFC失败
* 故障编号：urma_628
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfc`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jfc
#### 7.43 删除ioctl的ioctl调用返回失败
* 故障编号：urma_629
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfc`，匹配`ioctl failed in urma_cmd_delete_jfc , ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交删除ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_delete_jfc
#### 7.44 删除JFC过程中依赖步骤失败
* 故障编号：urma_630
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfc`，匹配`There is jfc event and it must be acked, jfc_comp:`，匹配`, comp:`，匹配`, jfc_async:`，匹配`, async:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_delete_jfc
#### 7.45 删除JFC所需输入对象无效导致删除JFC失败
* 故障编号：urma_631
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfc_batch`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFC，调用方传入的删除JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jfc_batch
#### 7.46 URMA context无效导致删除JFC失败
* 故障编号：urma_632
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfc_batch`，匹配`Invalid parameter, index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jfc_batch
#### 7.47 URMA context无效导致删除JFC失败
* 故障编号：urma_633
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfc_batch`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_delete_jfc_batch
#### 7.48 JFC清理阶段下层释放操作失败
* 故障编号：urma_634
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfc_batch`，匹配`jfc not from the same dev, cannot delete in a batch, index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFC相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_cmd_delete_jfc_batch
#### 7.49 删除ioctl的ioctl调用返回失败
* 故障编号：urma_635
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfc_batch`，匹配`ioctl failed in urma_cmd_delete_jfc_batch , ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交删除ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_delete_jfc_batch
#### 7.50 删除JFC过程中依赖步骤失败
* 故障编号：urma_636
* 故障现象：
    * 关键日志：匹配`urma_cmd_delete_jfc_batch`，匹配`bad jfc index exceed array length, bad_jfc_index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_delete_jfc_batch
#### 7.51 URMA context无效导致释放JFC失败
* 故障编号：urma_637
* 故障现象：
    * 关键日志：匹配`urma_cmd_free_jfc`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_free_jfc
#### 7.52 删除ioctl的ioctl调用返回失败
* 故障编号：urma_638
* 故障现象：
    * 关键日志：匹配`urma_cmd_free_jfc`，匹配`ioctl failed in urma_cmd_delete_jfc , ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交删除ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_free_jfc
#### 7.53 释放JFC过程中依赖步骤失败
* 故障编号：urma_639
* 故障现象：
    * 关键日志：匹配`urma_cmd_free_jfc`，匹配`There is jfc event and it must be acked, jfc_comp:`，匹配`, comp:`，匹配`, jfc_async:`，匹配`, async:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_free_jfc
#### 7.54 URMA context、JFR对象无效导致释放JFR失败
* 故障编号：urma_640
* 故障现象：
    * 关键日志：匹配`urma_cmd_free_jfr`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_free_jfr
#### 7.55 删除ioctl的ioctl调用返回失败
* 故障编号：urma_641
* 故障现象：
    * 关键日志：匹配`urma_cmd_free_jfr`，匹配`ioctl failed in urma_cmd_delete_jfr , ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交删除ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_free_jfr
#### 7.56 URMA context、provider操作表无效导致释放JFC失败
* 故障编号：urma_642
* 故障现象：
    * 关键日志：匹配`urma_free_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放JFC，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_free_jfc
#### 7.57 释放JFC过程中依赖步骤失败
* 故障编号：urma_643
* 故障现象：
    * 关键日志：匹配`urma_free_jfc`，匹配`jfc still actived, please deactived first`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_free_jfc
#### 7.58 URMA context、provider操作表、provider未提供free_jfc操作实现无效导致释放JFC失败
* 故障编号：urma_644
* 故障现象：
    * 关键日志：匹配`urma_free_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放JFC，调用方传入的URMA context、provider操作表、provider未提供free_jfc操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_free_jfc
#### 7.59 URMA context、provider操作表无效导致删除JFC失败
* 故障编号：urma_645
* 故障现象：
    * 关键日志：匹配`urma_delete_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFC，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfc
#### 7.60 JFC清理阶段下层释放操作失败
* 故障编号：urma_646
* 故障现象：
    * 关键日志：匹配`urma_delete_jfc`，匹配`jfc is deactived, can not delete.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFC相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_jfc
#### 7.61 URMA context、provider操作表、provider未提供delete_jfc操作实现无效导致删除JFC失败
* 故障编号：urma_647
* 故障现象：
    * 关键日志：匹配`urma_delete_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFC，调用方传入的URMA context、provider操作表、provider未提供delete_jfc操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfc
#### 7.62 JFC清理阶段下层释放操作失败
* 故障编号：urma_648
* 故障现象：
    * 关键日志：匹配`urma_delete_jfc`，匹配`[DRV_ERR]Failed to delete jfc, dev_name:`，匹配`, eid_idx:`，匹配`, id:`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFC相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_jfc
#### 7.63 URMA context、provider操作表无效导致删除JFC失败
* 故障编号：urma_649
* 故障现象：
    * 关键日志：匹配`urma_delete_jfc_batch`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFC，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfc_batch
#### 7.64 删除JFC所需输入对象无效导致删除JFC失败
* 故障编号：urma_650
* 故障现象：
    * 关键日志：匹配`urma_delete_jfc_batch`，匹配`Invalid parameter,`，匹配`jfc in the array is NULL.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFC，调用方传入的删除JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfc_batch
#### 7.65 URMA context、设备对象、sysfs设备信息、provider操作表无效导致删除JFC失败
* 故障编号：urma_651
* 故障现象：
    * 关键日志：匹配`urma_delete_jfc_batch`，匹配`Invalid parameter, index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFC，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfc_batch
#### 7.66 URMA context、provider操作表、JFS对象无效导致释放JFS失败
* 故障编号：urma_652
* 故障现象：
    * 关键日志：匹配`urma_free_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放JFS，调用方传入的URMA context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_free_jfs
#### 7.67 释放JFS过程中依赖步骤失败
* 故障编号：urma_653
* 故障现象：
    * 关键日志：匹配`urma_free_jfs`，匹配`jfs still actived, please deactived first`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_free_jfs
#### 7.68 URMA context、provider操作表、JFS对象、provider未提供free_jfs操作实现无效导致释放JFS失败
* 故障编号：urma_654
* 故障现象：
    * 关键日志：匹配`urma_free_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放JFS，调用方传入的URMA context、provider操作表、JFS对象、provider未提供free_jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_free_jfs
#### 7.69 JFS清理阶段下层释放操作失败
* 故障编号：urma_655
* 故障现象：
    * 关键日志：匹配`urma_free_jfs`，匹配`Failed to free jfs.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_free_jfs
#### 7.70 URMA context、JFS对象无效导致删除JFS失败
* 故障编号：urma_656
* 故障现象：
    * 关键日志：匹配`urma_delete_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfs
#### 7.71 JFS清理阶段下层释放操作失败
* 故障编号：urma_657
* 故障现象：
    * 关键日志：匹配`urma_delete_jfs`，匹配`jfs is deactived, can not delete.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_jfs
#### 7.72 URMA context、provider操作表、JFS对象、provider未提供delete_jfs操作实现无效导致删除JFS失败
* 故障编号：urma_658
* 故障现象：
    * 关键日志：匹配`urma_delete_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFS，调用方传入的URMA context、provider操作表、JFS对象、provider未提供delete_jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfs
#### 7.73 JFS清理阶段下层释放操作失败
* 故障编号：urma_659
* 故障现象：
    * 关键日志：匹配`urma_delete_jfs`，匹配`[DRV_ERR]Failed to delete jfs, dev_name:`，匹配`, eid_idx:`，匹配`, id:`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_jfs
#### 7.74 URMA context、provider操作表、JFS对象无效导致删除JFS失败
* 故障编号：urma_660
* 故障现象：
    * 关键日志：匹配`urma_delete_jfs_batch`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFS，调用方传入的URMA context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfs_batch
#### 7.75 JFS对象无效导致删除JFS失败
* 故障编号：urma_661
* 故障现象：
    * 关键日志：匹配`urma_delete_jfs_batch`，匹配`Invalid parameter, index:`，匹配`jfs in the array is NULL.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFS，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfs_batch
#### 7.76 URMA context、设备对象、sysfs设备信息、provider操作表、JFS对象无效导致删除JFS失败
* 故障编号：urma_662
* 故障现象：
    * 关键日志：匹配`urma_delete_jfs_batch`，匹配`Invalid parameter, index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFS，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfs_batch
#### 7.77 JFS清理阶段下层释放操作失败
* 故障编号：urma_663
* 故障现象：
    * 关键日志：匹配`urma_delete_jfs_batch`，匹配`Failed to delete jfs batch.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFS相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_jfs_batch
#### 7.78 URMA context、provider操作表、JFR对象无效导致释放JFR失败
* 故障编号：urma_664
* 故障现象：
    * 关键日志：匹配`urma_free_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放JFR，调用方传入的URMA context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_free_jfr
#### 7.79 释放JFR过程中依赖步骤失败
* 故障编号：urma_665
* 故障现象：
    * 关键日志：匹配`urma_free_jfr`，匹配`jfr still actived, please deactived first`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_free_jfr
#### 7.80 URMA context、provider操作表、JFR对象、provider未提供free_jfr操作实现无效导致释放JFR失败
* 故障编号：urma_666
* 故障现象：
    * 关键日志：匹配`urma_free_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放JFR，调用方传入的URMA context、provider操作表、JFR对象、provider未提供free_jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_free_jfr
#### 7.81 JFR清理阶段下层释放操作失败
* 故障编号：urma_667
* 故障现象：
    * 关键日志：匹配`urma_free_jfr`，匹配`Failed to free jfr.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_free_jfr
#### 7.82 URMA context、JFR对象无效导致删除JFR失败
* 故障编号：urma_668
* 故障现象：
    * 关键日志：匹配`urma_delete_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfr
#### 7.83 JFR清理阶段下层释放操作失败
* 故障编号：urma_669
* 故障现象：
    * 关键日志：匹配`urma_delete_jfr`，匹配`jfr is deactived, can not delete.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_jfr
#### 7.84 URMA context、provider操作表、JFR对象、provider未提供delete_jfr操作实现无效导致删除JFR失败
* 故障编号：urma_670
* 故障现象：
    * 关键日志：匹配`urma_delete_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFR，调用方传入的URMA context、provider操作表、JFR对象、provider未提供delete_jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfr
#### 7.85 JFR清理阶段下层释放操作失败
* 故障编号：urma_671
* 故障现象：
    * 关键日志：匹配`urma_delete_jfr`，匹配`[DRV_ERR]Failed to delete jfr, dev_name:`，匹配`, eid_idx:`，匹配`, id:`，匹配`, status:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_jfr
#### 7.86 URMA context、provider操作表、JFR对象无效导致删除JFR失败
* 故障编号：urma_672
* 故障现象：
    * 关键日志：匹配`urma_delete_jfr_batch`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFR，调用方传入的URMA context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfr_batch
#### 7.87 JFR对象无效导致删除JFR失败
* 故障编号：urma_673
* 故障现象：
    * 关键日志：匹配`urma_delete_jfr_batch`，匹配`Invalid parameter, index:`，匹配`jfr in the array is NULL.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFR，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfr_batch
#### 7.88 URMA context、设备对象、sysfs设备信息、provider操作表、JFR对象无效导致删除JFR失败
* 故障编号：urma_674
* 故障现象：
    * 关键日志：匹配`urma_delete_jfr_batch`，匹配`Invalid parameter, index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFR，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_jfr_batch
#### 7.89 JFR清理阶段下层释放操作失败
* 故障编号：urma_675
* 故障现象：
    * 关键日志：匹配`urma_delete_jfr_batch`，匹配`Failed to delete jfr batch.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_jfr_batch
#### 7.90 URMA context、设备对象无效导致删除JFCE失败
* 故障编号：urma_676
* 故障现象：
    * 关键日志：匹配`urma_delete_jfce`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFCE，调用方传入的URMA context、设备对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：当前不会触发
* 函数名：urma_delete_jfce
#### 7.91 删除JFCE过程中依赖步骤失败
* 故障编号：urma_677
* 故障现象：
    * 关键日志：匹配`urma_delete_jfce`，匹配`Jfce is still used by at least one jfc, refcnt:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFCE，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：当前不会触发
* 函数名：urma_delete_jfce
#### 7.92 URMA context、provider操作表、provider未提供delete_jfce操作实现无效导致删除JFCE失败
* 故障编号：urma_678
* 故障现象：
    * 关键日志：匹配`urma_delete_jfce`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除JFCE，调用方传入的URMA context、provider操作表、provider未提供delete_jfce操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：当前不会触发
* 函数名：urma_delete_jfce
#### 7.93 JFCE清理阶段下层释放操作失败
* 故障编号：urma_679
* 故障现象：
    * 关键日志：匹配`urma_delete_jfce`，匹配`[DRV_ERR]Failed to delete jfce, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销JFCE相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：当前不会触发
* 函数名：urma_delete_jfce
#### 7.94 URMA context、provider操作表无效导致删除Notifier失败
* 故障编号：urma_680
* 故障现象：
    * 关键日志：匹配`urma_delete_notifier`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Notifier，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_notifier
#### 7.95 URMA context、provider操作表、provider未提供delete_notifier操作实现无效导致删除Notifier失败
* 故障编号：urma_681
* 故障现象：
    * 关键日志：匹配`urma_delete_notifier`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Notifier，调用方传入的URMA context、provider操作表、provider未提供delete_notifier操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_notifier
#### 7.96 URMA context、provider操作表、provider未提供ack_notify操作实现无效导致删除Notifier失败
* 故障编号：urma_682
* 故障现象：
    * 关键日志：匹配`urma_delete_notifier`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除Notifier，调用方传入的URMA context、provider操作表、provider未提供ack_notify操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_delete_notifier
#### 7.97 Notifier清理阶段下层释放操作失败
* 故障编号：urma_683
* 故障现象：
    * 关键日志：匹配`urma_delete_notifier`，匹配`Failed to delete notifier, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数负责释放或撤销Notifier相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。
* 解决办法：无
* 函数名：urma_delete_notifier
#### 7.98 释放URMA资源所需输入对象无效导致释放URMA资源失败
* 故障编号：urma_684
* 故障现象：
    * 关键日志：匹配`urma_free_net_addr_list`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放URMA资源，调用方传入的释放URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_free_net_addr_list
#### 7.99 释放EID过程中依赖步骤失败
* 故障编号：urma_685
* 故障现象：
    * 关键日志：匹配`urma_free_device_list`，匹配`max eid cnt`，匹配`is err`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_free_device_list
#### 7.100 URMA context、设备对象、provider操作表无效导致删除context失败
* 故障编号：urma_686
* 故障现象：
    * 关键日志：匹配`urma_delete_context`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于删除context，调用方传入的URMA context、设备对象、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：当前不会触发
* 函数名：urma_delete_context

## 8 设备/驱动交互失败
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 8.1 设置文件描述符过程中依赖步骤失败
* 故障编号：urma_687
* 故障现象：
    * 关键日志：匹配`set_fd_noblock`，匹配`flags:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置文件描述符，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：set_fd_noblock
#### 8.2 设置文件描述符过程中依赖步骤失败
* 故障编号：urma_688
* 故障现象：
    * 关键日志：匹配`set_fd_noblock`，匹配`ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置文件描述符，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：set_fd_noblock
#### 8.3 修改ioctl的ioctl调用返回失败
* 故障编号：urma_689
* 故障现象：
    * 关键日志：匹配`urma_cmd_modify_jfs`，匹配`ioctl failed in urma_cmd_modify_jfs, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交修改ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_modify_jfs
#### 8.4 设置ioctl的ioctl调用返回失败
* 故障编号：urma_690
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jfs_opt`，匹配`ioctl failed in urma_cmd_set_jfs_opt, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交设置ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_set_jfs_opt
#### 8.5 激活ioctl的ioctl调用返回失败
* 故障编号：urma_691
* 故障现象：
    * 关键日志：匹配`urma_cmd_active_jfs`，匹配`ioctl failed in urma_cmd_active_jfs, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交激活ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_active_jfs
#### 8.6 去激活ioctl的ioctl调用返回失败
* 故障编号：urma_692
* 故障现象：
    * 关键日志：匹配`urma_cmd_deactive_jfs`，匹配`ioctl failed in urma_cmd_deactive_jfs, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交去激活ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_deactive_jfs
#### 8.7 修改ioctl的ioctl调用返回失败
* 故障编号：urma_693
* 故障现象：
    * 关键日志：匹配`urma_cmd_modify_jfr`，匹配`ioctl failed in urma_cmd_modify_jfr, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交修改ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_modify_jfr
#### 8.8 修改ioctl的ioctl调用返回失败
* 故障编号：urma_694
* 故障现象：
    * 关键日志：匹配`urma_cmd_modify_jfc`，匹配`ioctl failed in urma_cmd_modify_jfc, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交修改ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_modify_jfc
#### 8.9 设置ioctl的ioctl调用返回失败
* 故障编号：urma_695
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jfc_opt`，匹配`ioctl failed in urma_cmd_set_jfc_opt, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交设置ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_set_jfc_opt
#### 8.10 激活ioctl的ioctl调用返回失败
* 故障编号：urma_696
* 故障现象：
    * 关键日志：匹配`urma_cmd_active_jfc`，匹配`ioctl failed in urma_cmd_active_jfc, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交激活ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_active_jfc
#### 8.11 激活ioctl的ioctl调用返回失败
* 故障编号：urma_697
* 故障现象：
    * 关键日志：匹配`urma_cmd_deactive_jfc`，匹配`ioctl failed in urma_cmd_active_jfc, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交激活ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_deactive_jfc
#### 8.12 设置ioctl的ioctl调用返回失败
* 故障编号：urma_698
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jfr_opt`，匹配`ioctl failed in urma_cmd_set_jfr_opt, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交设置ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_set_jfr_opt
#### 8.13 激活ioctl的ioctl调用返回失败
* 故障编号：urma_699
* 故障现象：
    * 关键日志：匹配`urma_cmd_active_jfr`，匹配`ioctl failed in urma_cmd_active_jfr, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交激活ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_active_jfr
#### 8.14 去激活ioctl的ioctl调用返回失败
* 故障编号：urma_700
* 故障现象：
    * 关键日志：匹配`urma_cmd_deactive_jfr`，匹配`ioctl failed in urma_cmd_deactive_jfr, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交去激活ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_cmd_deactive_jfr
#### 8.15 等待JFC过程中依赖步骤失败
* 故障编号：urma_701
* 故障现象：
    * 关键日志：匹配`urma_cmd_wait_jfc`，匹配`Faile to wait jfc non-block, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于等待JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_wait_jfc
#### 8.16 执行ioctl的ioctl调用返回失败
* 故障编号：urma_702
* 故障现象：
    * 关键日志：匹配`urma_tlv_ioctl`，匹配`ioctl failed, ret:`，匹配`, errno:`，匹配`, cmd:`，匹配`, kdrv_err:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交执行ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。URMA内核态调用驱动异常，返回错误码2048，则容器中用户态日志出现ioctl失败，并且errno为特定的2048，故障发生在内核态驱动
* 解决办法：UDMA驱动相关，需进一步排查硬件
* 函数名：urma_tlv_ioctl
#### 8.17 执行wait jfc驱动命令的ioctl调用返回失败
* 故障编号：urma_703
* 故障现象：
    * 关键日志：匹配`urma_ioctl_wait_jfc`，匹配`wait jfc ioctl failed, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交执行wait jfc驱动命令请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_ioctl_wait_jfc
#### 8.18 执行wait notify驱动命令的ioctl调用返回失败
* 故障编号：urma_704
* 故障现象：
    * 关键日志：匹配`urma_ioctl_wait_notify`，匹配`wait notify ioctl failed, ret:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数通过ioctl向URMA内核驱动提交执行wait notify驱动命令请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。
* 解决办法：无
* 函数名：urma_ioctl_wait_notify
#### 8.19 设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败
* 故障编号：urma_705
* 故障现象：
    * 关键日志：匹配`urma_discover_devices`，匹配`open failed, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_discover_devices
#### 8.20 分配设备过程中依赖步骤失败
* 故障编号：urma_706
* 故障现象：
    * 关键日志：匹配`urma_discover_devices`，匹配`Failed close dir:`，匹配`, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_discover_devices
#### 8.21 打开URMA资源过程中依赖步骤失败
* 故障编号：urma_707
* 故障现象：
    * 关键日志：匹配`urma_open_drivers`，匹配`strrchr`，匹配`failed, errno:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于打开URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_open_drivers
#### 8.22 打开字符设备过程中依赖步骤失败
* 故障编号：urma_708
* 故障现象：
    * 关键日志：匹配`urma_open_cdev`，匹配`file_path:`，匹配`is not standardize.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于打开字符设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_open_cdev
#### 8.23 设置设备过程中依赖步骤失败
* 故障编号：urma_709
* 故障现象：
    * 关键日志：匹配`urma_set_context_opt`，匹配`Cannot set aggregated mode for non-aggregated device.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_context_opt

## 9 其他URMA故障
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 9.1 修改物理 JFC过程中依赖步骤失败
* 故障编号：urma_710
* 故障现象：
    * 关键日志：匹配`bondp_modify_jfc`，匹配`modify pjfc fail, index:`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改物理 JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_modify_jfc
#### 9.2 激活端口所需输入对象无效导致激活端口失败
* 故障编号：urma_711
* 故障现象：
    * 关键日志：匹配`convert_bond_port_id_to_active_index`，匹配`Invalid primary chip_id:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活端口，调用方传入的激活端口所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：convert_bond_port_id_to_active_index
#### 9.3 激活端口所需输入对象无效导致激活端口失败
* 故障编号：urma_712
* 故障现象：
    * 关键日志：匹配`convert_bond_port_id_to_active_index`，匹配`Invalid port id, chip_id:`，匹配`, port_idx:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活端口，调用方传入的激活端口所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：convert_bond_port_id_to_active_index
#### 9.4 激活端口所需输入对象无效导致激活端口失败
* 故障编号：urma_713
* 故障现象：
    * 关键日志：匹配`convert_bond_port_id_to_active_index`，匹配`Invalid converted active index:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活端口，调用方传入的激活端口所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：convert_bond_port_id_to_active_index
#### 9.5 修改物理 JFS过程中依赖步骤失败
* 故障编号：urma_714
* 故障现象：
    * 关键日志：匹配`bondp_modify_jfs`，匹配`modify pjfs fail, index:`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改物理 JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_modify_jfs
#### 9.6 修改物理 JFR过程中依赖步骤失败
* 故障编号：urma_715
* 故障现象：
    * 关键日志：匹配`bondp_modify_jfr`，匹配`modify pjfr fail, index:`，匹配`, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改物理 JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_modify_jfr
#### 9.7 URMA context无效导致设置Jetty失败
* 故障编号：urma_716
* 故障现象：
    * 关键日志：匹配`bondp_user_ctl_set_bonding_mode_legacy`，匹配`Invalid set bonding mode legacy param.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Jetty，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_user_ctl_set_bonding_mode_legacy
#### 9.8 URMA context无效导致设置context失败
* 故障编号：urma_717
* 故障现象：
    * 关键日志：匹配`bondp_user_ctl_set_bonding_mode_legacy`，匹配`Invalid aggr mode:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_user_ctl_set_bonding_mode_legacy
#### 9.9 URMA context无效导致设置context失败
* 故障编号：urma_718
* 故障现象：
    * 关键日志：匹配`bondp_user_ctl_set_bonding_mode`，匹配`Invalid set bonding mode param.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_user_ctl_set_bonding_mode
#### 9.10 设置context过程中依赖步骤失败
* 故障编号：urma_719
* 故障现象：
    * 关键日志：匹配`bondp_user_ctl`，匹配`Unsupported opcode, opcode:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_user_ctl
#### 9.11 执行JFC过程中依赖步骤失败
* 故障编号：urma_720
* 故障现象：
    * 关键日志：匹配`bondp_rearm_jfc`，匹配`Failed to rearm jfc: JFCE is NULL`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_rearm_jfc
#### 9.12 确认URMA资源所需输入对象无效导致确认URMA资源失败
* 故障编号：urma_721
* 故障现象：
    * 关键日志：匹配`bondp_ack_async_event`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于确认URMA资源，调用方传入的确认URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_ack_async_event
#### 9.13 URMA context无效导致设置context失败
* 故障编号：urma_722
* 故障现象：
    * 关键日志：匹配`bondp_set_bonding_mode`，匹配`Invalid context.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_set_bonding_mode
#### 9.14 URMA context、设备对象无效导致设置context失败
* 故障编号：urma_723
* 故障现象：
    * 关键日志：匹配`bondp_set_bonding_mode`，匹配`Invalid bonding mode:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置context，调用方传入的URMA context、设备对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bondp_set_bonding_mode
#### 9.15 设置设备过程中依赖步骤失败
* 故障编号：urma_724
* 故障现象：
    * 关键日志：匹配`bondp_set_bonding_mode`，匹配`Unsupported bonding level:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bondp_set_bonding_mode
#### 9.16 执行URMA资源所需输入对象无效导致释放URMA资源失败
* 故障编号：urma_725
* 故障现象：
    * 关键日志：匹配`bdp_slide_wnd_seq_in_window`，匹配`Invalid param wnd`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放URMA资源，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bdp_slide_wnd_seq_in_window
#### 9.17 释放URMA资源过程中依赖步骤失败
* 故障编号：urma_726
* 故障现象：
    * 关键日志：匹配`bdp_slide_wnd_seq_in_window`，匹配`Seq larger than total size of bitmap`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bdp_slide_wnd_seq_in_window
#### 9.18 执行URMA资源所需输入对象无效导致执行URMA资源失败
* 故障编号：urma_727
* 故障现象：
    * 关键日志：匹配`bdp_slide_wnd_has`，匹配`Invalid param wnd`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行URMA资源，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bdp_slide_wnd_has
#### 9.19 设置URMA资源过程中依赖步骤失败
* 故障编号：urma_728
* 故障现象：
    * 关键日志：匹配`bdp_slide_wnd_has`，匹配`Seq larger than total size of bitmap`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：bdp_slide_wnd_has
#### 9.20 执行URMA资源所需输入对象无效导致设置URMA资源失败
* 故障编号：urma_729
* 故障现象：
    * 关键日志：匹配`bdp_slide_wnd_add`，匹配`Invalid param wnd`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置URMA资源，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：bdp_slide_wnd_add
#### 9.21 执行EID过程中依赖步骤失败
* 故障编号：urma_730
* 故障现象：
    * 关键日志：匹配`update_mapping_hash_table`，匹配`Failed to add agg eid to mapping hash table`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：update_mapping_hash_table
#### 9.22 执行EID过程中依赖步骤失败
* 故障编号：urma_731
* 故障现象：
    * 关键日志：匹配`update_mapping_hash_table`，匹配`Failed to add primary eid to mapping hash table`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：update_mapping_hash_table
#### 9.23 执行端口过程中依赖步骤失败
* 故障编号：urma_732
* 故障现象：
    * 关键日志：匹配`update_mapping_hash_table`，匹配`Failed to add port eid to mapping hash table`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行端口，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：update_mapping_hash_table
#### 9.24 释放URMA资源过程中依赖步骤失败
* 故障编号：urma_733
* 故障现象：
    * 关键日志：匹配`update_mapping_hash_table`，匹配`topo info doesn't have cur_node`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：update_mapping_hash_table
#### 9.25 等待锁过程中依赖步骤失败
* 故障编号：urma_734
* 故障现象：
    * 关键日志：匹配`wait_async_event_ack`，匹配`There is an event and it must be acked, acked:`，匹配`, reported:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于等待锁，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：wait_async_event_ack
#### 9.26 URMA context、JFS对象无效导致修改JFS失败
* 故障编号：urma_735
* 故障现象：
    * 关键日志：匹配`urma_cmd_modify_jfs`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_modify_jfs
#### 9.27 URMA context、JFS对象无效导致设置JFS失败
* 故障编号：urma_736
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jfs_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_set_jfs_opt
#### 9.28 URMA context、JFS对象无效导致设置JFS失败
* 故障编号：urma_737
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jfs_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_set_jfs_opt
#### 9.29 设置JFC过程中依赖步骤失败
* 故障编号：urma_738
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jfs_opt`，匹配`jfc not exist in jfs.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_set_jfs_opt
#### 9.30 URMA context、JFS对象无效导致激活JFS失败
* 故障编号：urma_739
* 故障现象：
    * 关键日志：匹配`urma_cmd_active_jfs`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_active_jfs
#### 9.31 URMA context、JFS对象无效导致去激活JFS失败
* 故障编号：urma_740
* 故障现象：
    * 关键日志：匹配`urma_cmd_deactive_jfs`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_deactive_jfs
#### 9.32 URMA context、JFS对象、JFR对象无效导致修改JFR失败
* 故障编号：urma_741
* 故障现象：
    * 关键日志：匹配`urma_cmd_modify_jfr`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改JFR，调用方传入的URMA context、JFS对象、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_modify_jfr
#### 9.33 URMA context无效导致修改JFC失败
* 故障编号：urma_742
* 故障现象：
    * 关键日志：匹配`urma_cmd_modify_jfc`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_modify_jfc
#### 9.34 URMA context无效导致设置JFC失败
* 故障编号：urma_743
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jfc_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_set_jfc_opt
#### 9.35 URMA context无效导致设置JFC失败
* 故障编号：urma_744
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jfc_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_set_jfc_opt
#### 9.36 URMA context无效导致激活JFC失败
* 故障编号：urma_745
* 故障现象：
    * 关键日志：匹配`urma_cmd_active_jfc`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_active_jfc
#### 9.37 URMA context无效导致去激活JFC失败
* 故障编号：urma_746
* 故障现象：
    * 关键日志：匹配`urma_cmd_deactive_jfc`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_deactive_jfc
#### 9.38 URMA context、JFS对象无效导致执行JFR失败
* 故障编号：urma_747
* 故障现象：
    * 关键日志：匹配`urma_cmd_advise_jfr`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行JFR，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_advise_jfr
#### 9.39 URMA context、JFS对象无效导致设置JFR失败
* 故障编号：urma_748
* 故障现象：
    * 关键日志：匹配`urma_cmd_unadvise_jfr`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFR，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_unadvise_jfr
#### 9.40 URMA context、JFR对象无效导致设置JFR失败
* 故障编号：urma_749
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jfr_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_set_jfr_opt
#### 9.41 URMA context、JFR对象无效导致设置JFR失败
* 故障编号：urma_750
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jfr_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_set_jfr_opt
#### 9.42 设置JFC过程中依赖步骤失败
* 故障编号：urma_751
* 故障现象：
    * 关键日志：匹配`urma_cmd_set_jfr_opt`，匹配`jfc not exist in jfr.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_cmd_set_jfr_opt
#### 9.43 URMA context、JFR对象无效导致激活JFR失败
* 故障编号：urma_752
* 故障现象：
    * 关键日志：匹配`urma_cmd_active_jfr`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_active_jfr
#### 9.44 URMA context、JFR对象无效导致去激活JFR失败
* 故障编号：urma_753
* 故障现象：
    * 关键日志：匹配`urma_cmd_deactive_jfr`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_deactive_jfr
#### 9.45 等待JFC所需输入对象无效导致等待JFC失败
* 故障编号：urma_754
* 故障现象：
    * 关键日志：匹配`urma_cmd_wait_jfc`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于等待JFC，调用方传入的等待JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_wait_jfc
#### 9.46 确认JFC所需输入对象无效导致确认JFC失败
* 故障编号：urma_755
* 故障现象：
    * 关键日志：匹配`urma_cmd_ack_jfc`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于确认JFC，调用方传入的确认JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_ack_jfc
#### 9.47 JFS对象、JFR对象、Jetty对象无效导致确认JFC失败
* 故障编号：urma_756
* 故障现象：
    * 关键日志：匹配`urma_cmd_ack_async_event`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于确认JFC，调用方传入的JFS对象、JFR对象、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_ack_async_event
#### 9.48 URMA context无效导致确认Jetty失败
* 故障编号：urma_757
* 故障现象：
    * 关键日志：匹配`urma_cmd_user_ctl`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于确认Jetty，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_user_ctl
#### 9.49 URMA context无效导致等待ioctl失败
* 故障编号：urma_758
* 故障现象：
    * 关键日志：匹配`urma_cmd_wait_notify`，匹配`Invalid parameter`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于等待ioctl，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_cmd_wait_notify
#### 9.50 执行URMA资源所需输入对象无效导致执行JFS失败
* 故障编号：urma_759
* 故障现象：
    * 关键日志：匹配`urma_check_opt_valid`，匹配`invalid opt len`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行JFS，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_opt_valid
#### 9.51 URMA context无效导致创建JFC失败
* 故障编号：urma_760
* 故障现象：
    * 关键日志：匹配`urma_check_trans_mode_valid`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_trans_mode_valid
#### 9.52 URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jfc操作实现无效导致创建JFC失败
* 故障编号：urma_761
* 故障现象：
    * 关键日志：匹配`urma_check_trans_mode_valid`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFC，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jfc操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_trans_mode_valid
#### 9.53 创建JFC过程中依赖步骤失败
* 故障编号：urma_762
* 故障现象：
    * 关键日志：匹配`urma_check_trans_mode_valid`，匹配`jfc cfg depth of range, depth:`，匹配`, max_depth:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_check_trans_mode_valid
#### 9.54 URMA context、设备对象无效导致修改JFC失败
* 故障编号：urma_763
* 故障现象：
    * 关键日志：匹配`urma_modify_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改JFC，调用方传入的URMA context、设备对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_modify_jfc
#### 9.55 URMA context、provider操作表、provider未提供modify_jfc操作实现无效导致修改JFC失败
* 故障编号：urma_764
* 故障现象：
    * 关键日志：匹配`urma_modify_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改JFC，调用方传入的URMA context、provider操作表、provider未提供modify_jfc操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_modify_jfc
#### 9.56 设置JFC所需输入对象无效导致设置JFC失败
* 故障编号：urma_765
* 故障现象：
    * 关键日志：匹配`urma_set_jfc_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFC，调用方传入的设置JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_jfc_opt
#### 9.57 设置JFC过程中依赖步骤失败
* 故障编号：urma_766
* 故障现象：
    * 关键日志：匹配`urma_set_jfc_opt`，匹配`Failed to set opt, jfc has been activated`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_jfc_opt
#### 9.58 provider操作表无效导致设置JFC失败
* 故障编号：urma_767
* 故障现象：
    * 关键日志：匹配`urma_set_jfc_opt`，匹配`invalid opt id or opt len`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFC，调用方传入的provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_jfc_opt
#### 9.59 URMA context、provider操作表、provider未提供set_jfc_opt操作实现无效导致设置JFC失败
* 故障编号：urma_768
* 故障现象：
    * 关键日志：匹配`urma_set_jfc_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFC，调用方传入的URMA context、provider操作表、provider未提供set_jfc_opt操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_jfc_opt
#### 9.60 设置JFC过程中依赖步骤失败
* 故障编号：urma_769
* 故障现象：
    * 关键日志：匹配`urma_set_jfc_opt`，匹配`Failed to exec ops->set_jfc_opt.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_jfc_opt
#### 9.61 设置JFC过程中依赖步骤失败
* 故障编号：urma_770
* 故障现象：
    * 关键日志：匹配`urma_set_jfc_opt`，匹配`Failed to exec urma_jfc_set_options.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_jfc_opt
#### 9.62 provider操作表无效导致激活JFC失败
* 故障编号：urma_771
* 故障现象：
    * 关键日志：匹配`urma_active_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFC，调用方传入的provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_active_jfc
#### 9.63 激活JFC过程中依赖步骤失败
* 故障编号：urma_772
* 故障现象：
    * 关键日志：匹配`urma_active_jfc`，匹配`jfc cfg depth of range, depth:`，匹配`, max_depth:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_active_jfc
#### 9.64 URMA context、provider操作表、provider未提供active_jfc操作实现无效导致激活JFC失败
* 故障编号：urma_773
* 故障现象：
    * 关键日志：匹配`urma_active_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFC，调用方传入的URMA context、provider操作表、provider未提供active_jfc操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_active_jfc
#### 9.65 激活JFC过程中依赖步骤失败
* 故障编号：urma_774
* 故障现象：
    * 关键日志：匹配`urma_active_jfc`，匹配`Failed to exec ops->active_jfc.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_active_jfc
#### 9.66 provider操作表无效导致去激活JFC失败
* 故障编号：urma_775
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFC，调用方传入的provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jfc
#### 9.67 URMA context、provider操作表、provider未提供deactive_jfc操作实现无效导致去激活JFC失败
* 故障编号：urma_776
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFC，调用方传入的URMA context、provider操作表、provider未提供deactive_jfc操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jfc
#### 9.68 去激活JFC过程中依赖步骤失败
* 故障编号：urma_777
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfc`，匹配`Failed to exec ops->deactive_jfc.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_deactive_jfc
#### 9.69 URMA context无效导致创建JFS失败
* 故障编号：urma_778
* 故障现象：
    * 关键日志：匹配`urma_check_order_type`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFS，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_order_type
#### 9.70 URMA context无效导致创建JFS失败
* 故障编号：urma_779
* 故障现象：
    * 关键日志：匹配`urma_check_order_type`，匹配`Invalid parameter, trans_mode:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFS，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_order_type
#### 9.71 执行URMA资源所需输入对象无效导致执行JFS失败
* 故障编号：urma_780
* 故障现象：
    * 关键日志：匹配`urma_check_order_type`，匹配`Invalid parameter, trans_mode:`，匹配`, order_type:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行JFS，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_order_type
#### 9.72 URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jfs操作实现无效导致创建JFS失败
* 故障编号：urma_781
* 故障现象：
    * 关键日志：匹配`urma_check_order_type`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFS，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_order_type
#### 9.73 创建JFS过程中依赖步骤失败
* 故障编号：urma_782
* 故障现象：
    * 关键日志：匹配`urma_check_order_type`，匹配`jfs cfg out of range, depth:`，匹配`, max_depth:`，匹配`, inline_data:`，匹配`, max_inline_len:`，匹配`, sge:`，匹配`hu, max_sge:`，匹配`, rsge:`，匹配`hu, max_rsge:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于创建JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_check_order_type
#### 9.74 URMA context、设备对象、JFS对象无效导致修改JFS失败
* 故障编号：urma_783
* 故障现象：
    * 关键日志：匹配`urma_modify_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改JFS，调用方传入的URMA context、设备对象、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_modify_jfs
#### 9.75 URMA context、provider操作表、JFS对象、provider未提供modify_jfs操作实现无效导致修改JFS失败
* 故障编号：urma_784
* 故障现象：
    * 关键日志：匹配`urma_modify_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改JFS，调用方传入的URMA context、provider操作表、JFS对象、provider未提供modify_jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_modify_jfs
#### 9.76 URMA context、provider操作表、JFS对象无效导致设置JFS失败
* 故障编号：urma_785
* 故障现象：
    * 关键日志：匹配`urma_set_jfs_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFS，调用方传入的URMA context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_jfs_opt
#### 9.77 设置JFS过程中依赖步骤失败
* 故障编号：urma_786
* 故障现象：
    * 关键日志：匹配`urma_set_jfs_opt`，匹配`Failed to set opt, jfs has been activated`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_jfs_opt
#### 9.78 provider操作表、JFS对象无效导致设置JFS失败
* 故障编号：urma_787
* 故障现象：
    * 关键日志：匹配`urma_set_jfs_opt`，匹配`invalid opt id or opt len`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFS，调用方传入的provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_jfs_opt
#### 9.79 URMA context、provider操作表、JFS对象、provider未提供set_jfs_opt操作实现无效导致设置JFS失败
* 故障编号：urma_788
* 故障现象：
    * 关键日志：匹配`urma_set_jfs_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFS，调用方传入的URMA context、provider操作表、JFS对象、provider未提供set_jfs_opt操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_jfs_opt
#### 9.80 设置JFR过程中依赖步骤失败
* 故障编号：urma_789
* 故障现象：
    * 关键日志：匹配`urma_set_jfs_opt`，匹配`Failed to exec urma_jfr_set_options.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_jfs_opt
#### 9.81 设置JFS过程中依赖步骤失败
* 故障编号：urma_790
* 故障现象：
    * 关键日志：匹配`urma_set_jfs_opt`，匹配`Failed to exec ops->set_jfs_opt.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_jfs_opt
#### 9.82 provider操作表、JFS对象无效导致激活JFS失败
* 故障编号：urma_791
* 故障现象：
    * 关键日志：匹配`urma_active_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFS，调用方传入的provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_active_jfs
#### 9.83 JFS对象无效导致激活JFS失败
* 故障编号：urma_792
* 故障现象：
    * 关键日志：匹配`urma_active_jfs`，匹配`Invalid parameter, trans_mode:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFS，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_active_jfs
#### 9.84 JFS对象无效导致激活JFS失败
* 故障编号：urma_793
* 故障现象：
    * 关键日志：匹配`urma_active_jfs`，匹配`Invalid parameter, trans_mode:`，匹配`, order_type:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFS，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_active_jfs
#### 9.85 URMA context、设备对象、sysfs设备信息、provider操作表、JFS对象、provider未提供active_jfs操作实现无效导致激活JFS失败
* 故障编号：urma_794
* 故障现象：
    * 关键日志：匹配`urma_active_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFS，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、JFS对象、provider未提供active_jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_active_jfs
#### 9.86 激活JFS过程中依赖步骤失败
* 故障编号：urma_795
* 故障现象：
    * 关键日志：匹配`urma_active_jfs`，匹配`jfs cfg out of range, depth:`，匹配`, max_depth:`，匹配`, inline_data:`，匹配`, max_inline_len:`，匹配`, sge:`，匹配`hu, max_sge:`，匹配`, rsge:`，匹配`hu, max_rsge:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_active_jfs
#### 9.87 激活JFS过程中依赖步骤失败
* 故障编号：urma_796
* 故障现象：
    * 关键日志：匹配`urma_active_jfs`，匹配`Failed to exec ops->active_jfs.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_active_jfs
#### 9.88 provider操作表、JFS对象无效导致去激活JFS失败
* 故障编号：urma_797
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFS，调用方传入的provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jfs
#### 9.89 URMA context、provider操作表、JFS对象、provider未提供deactive_jfs操作实现无效导致去激活JFS失败
* 故障编号：urma_798
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFS，调用方传入的URMA context、provider操作表、JFS对象、provider未提供deactive_jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jfs
#### 9.90 去激活JFS过程中依赖步骤失败
* 故障编号：urma_799
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfs`，匹配`Failed to exec ops->deactive_jfs.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_deactive_jfs
#### 9.91 URMA context、provider操作表、JFS对象无效导致去激活JFS失败
* 故障编号：urma_800
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFS，调用方传入的URMA context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jfs
#### 9.92 URMA context无效导致去激活JFS失败
* 故障编号：urma_801
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfs`，匹配`Invalid parameter, trans_mode:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFS，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jfs
#### 9.93 URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jfr操作实现无效导致去激活JFS失败
* 故障编号：urma_802
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfs`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFS，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jfs
#### 9.94 去激活JFR过程中依赖步骤失败
* 故障编号：urma_803
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfs`，匹配`jfr cfg out of range, depth:`，匹配`, max_depth:`，匹配`, sge:`，匹配`, max_sge:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_deactive_jfs
#### 9.95 URMA context、设备对象、JFR对象无效导致修改JFR失败
* 故障编号：urma_804
* 故障现象：
    * 关键日志：匹配`urma_modify_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改JFR，调用方传入的URMA context、设备对象、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_modify_jfr
#### 9.96 URMA context、provider操作表、JFR对象、provider未提供modify_jfr操作实现无效导致修改JFR失败
* 故障编号：urma_805
* 故障现象：
    * 关键日志：匹配`urma_modify_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于修改JFR，调用方传入的URMA context、provider操作表、JFR对象、provider未提供modify_jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_modify_jfr
#### 9.97 URMA context、provider操作表、目标Jetty对象、provider未提供import_jfr_ex操作实现无效导致导入JFR失败
* 故障编号：urma_806
* 故障现象：
    * 关键日志：匹配`urma_check_ctrlplane_compat`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于导入JFR，调用方传入的URMA context、provider操作表、目标Jetty对象、provider未提供import_jfr_ex操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_ctrlplane_compat
#### 9.98 URMA context、设备对象、sysfs设备信息、provider操作表、目标Jetty对象无效导致导入context失败
* 故障编号：urma_807
* 故障现象：
    * 关键日志：匹配`urma_check_ctrlplane_compat`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于导入context，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_ctrlplane_compat
#### 9.99 URMA context、provider操作表无效导致导入Jetty失败
* 故障编号：urma_808
* 故障现象：
    * 关键日志：匹配`urma_check_ctrlplane_compat`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于导入Jetty，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_ctrlplane_compat
#### 9.100 URMA context、provider操作表、provider未提供import_jfr_ex操作实现无效导致导入JFR失败
* 故障编号：urma_809
* 故障现象：
    * 关键日志：匹配`urma_check_ctrlplane_compat`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于导入JFR，调用方传入的URMA context、provider操作表、provider未提供import_jfr_ex操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_ctrlplane_compat
#### 9.101 URMA context、provider操作表、JFR对象无效导致设置JFR失败
* 故障编号：urma_810
* 故障现象：
    * 关键日志：匹配`urma_set_jfr_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFR，调用方传入的URMA context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_jfr_opt
#### 9.102 设置JFR过程中依赖步骤失败
* 故障编号：urma_811
* 故障现象：
    * 关键日志：匹配`urma_set_jfr_opt`，匹配`Failed to set opt, jfr has been activated`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_jfr_opt
#### 9.103 JFR对象无效导致设置JFR失败
* 故障编号：urma_812
* 故障现象：
    * 关键日志：匹配`urma_set_jfr_opt`，匹配`invalid opt id or opt len`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFR，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_jfr_opt
#### 9.104 设置JFR过程中依赖步骤失败
* 故障编号：urma_813
* 故障现象：
    * 关键日志：匹配`urma_set_jfr_opt`，匹配`Failed to exec urma_jfr_set_options.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_jfr_opt
#### 9.105 URMA context、provider操作表、JFR对象、provider未提供set_jfr_opt操作实现无效导致设置JFR失败
* 故障编号：urma_814
* 故障现象：
    * 关键日志：匹配`urma_set_jfr_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFR，调用方传入的URMA context、provider操作表、JFR对象、provider未提供set_jfr_opt操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_jfr_opt
#### 9.106 设置JFR过程中依赖步骤失败
* 故障编号：urma_815
* 故障现象：
    * 关键日志：匹配`urma_set_jfr_opt`，匹配`Failed to exec ops->set_jfr_opt.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_set_jfr_opt
#### 9.107 URMA context、provider操作表、JFR对象无效导致激活JFR失败
* 故障编号：urma_816
* 故障现象：
    * 关键日志：匹配`urma_active_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFR，调用方传入的URMA context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_active_jfr
#### 9.108 URMA context、provider操作表、JFR对象无效导致激活JFR失败
* 故障编号：urma_817
* 故障现象：
    * 关键日志：匹配`urma_active_jfr`，匹配`Invalid parameter, trans_mode:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFR，调用方传入的URMA context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_active_jfr
#### 9.109 URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供active_jfr操作实现无效导致激活JFR失败
* 故障编号：urma_818
* 故障现象：
    * 关键日志：匹配`urma_active_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFR，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供active_jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_active_jfr
#### 9.110 激活JFR过程中依赖步骤失败
* 故障编号：urma_819
* 故障现象：
    * 关键日志：匹配`urma_active_jfr`，匹配`jfr cfg out of range, depth:`，匹配`, max_depth:`，匹配`, sge:`，匹配`, max_sge:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_active_jfr
#### 9.111 激活JFR过程中依赖步骤失败
* 故障编号：urma_820
* 故障现象：
    * 关键日志：匹配`urma_active_jfr`，匹配`Failed to exec ops->active_jfr.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于激活JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_active_jfr
#### 9.112 provider操作表、JFR对象无效导致去激活JFR失败
* 故障编号：urma_821
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFR，调用方传入的provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jfr
#### 9.113 URMA context、provider操作表、JFR对象、provider未提供deactive_jfr操作实现无效导致去激活JFR失败
* 故障编号：urma_822
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFR，调用方传入的URMA context、provider操作表、JFR对象、provider未提供deactive_jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jfr
#### 9.114 去激活JFR过程中依赖步骤失败
* 故障编号：urma_823
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfr`，匹配`Failed to exec ops->deactive_jfr.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_deactive_jfr
#### 9.115 URMA context、provider操作表、JFR对象无效导致去激活JFR失败
* 故障编号：urma_824
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFR，调用方传入的URMA context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jfr
#### 9.116 URMA context、provider操作表、provider未提供create_jfce操作实现无效导致去激活JFR失败
* 故障编号：urma_825
* 故障现象：
    * 关键日志：匹配`urma_deactive_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于去激活JFR，调用方传入的URMA context、provider操作表、provider未提供create_jfce操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_deactive_jfr
#### 9.117 URMA context无效导致等待锁失败
* 故障编号：urma_826
* 故障现象：
    * 关键日志：匹配`urma_wait_notify`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于等待锁，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_wait_notify
#### 9.118 URMA context、provider操作表、provider未提供wait_notify操作实现无效导致等待Notifier失败
* 故障编号：urma_827
* 故障现象：
    * 关键日志：匹配`urma_wait_notify`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于等待Notifier，调用方传入的URMA context、provider操作表、provider未提供wait_notify操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_wait_notify
#### 9.119 URMA context、provider操作表、provider未提供ack_notify操作实现无效导致等待Notifier失败
* 故障编号：urma_828
* 故障现象：
    * 关键日志：匹配`urma_wait_notify`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于等待Notifier，调用方传入的URMA context、provider操作表、provider未提供ack_notify操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_wait_notify
#### 9.120 URMA context、provider操作表无效导致确认Jetty失败
* 故障编号：urma_829
* 故障现象：
    * 关键日志：匹配`urma_ack_notify`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于确认Jetty，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_ack_notify
#### 9.121 URMA context、provider操作表、provider未提供ack_notify操作实现无效导致确认context失败
* 故障编号：urma_830
* 故障现象：
    * 关键日志：匹配`urma_ack_notify`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于确认context，调用方传入的URMA context、provider操作表、provider未提供ack_notify操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_ack_notify
#### 9.122 URMA context、provider操作表无效导致确认context失败
* 故障编号：urma_831
* 故障现象：
    * 关键日志：匹配`urma_ack_notify`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于确认context，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_ack_notify
#### 9.123 URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jetty_grp操作实现无效导致确认Jetty失败
* 故障编号：urma_832
* 故障现象：
    * 关键日志：匹配`urma_ack_notify`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于确认Jetty，调用方传入的URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jetty_grp操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_ack_notify
#### 9.124 设置Segment过程中依赖步骤失败
* 故障编号：urma_833
* 故障现象：
    * 关键日志：匹配`urma_check_seg_cfg`，匹配`Local only access is not allowed to config with other accesses.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置Segment，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_check_seg_cfg
#### 9.125 URMA context、provider操作表、Segment对象无效导致注册Segment失败
* 故障编号：urma_834
* 故障现象：
    * 关键日志：匹配`urma_check_seg_cfg`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于注册Segment，调用方传入的URMA context、provider操作表、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_seg_cfg
#### 9.126 URMA context、设备对象、provider操作表、Segment对象、provider未提供register_seg操作实现无效导致注册Segment失败
* 故障编号：urma_835
* 故障现象：
    * 关键日志：匹配`urma_check_seg_cfg`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于注册Segment，调用方传入的URMA context、设备对象、provider操作表、Segment对象、provider未提供register_seg操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_check_seg_cfg
#### 9.127 URMA context、JFS对象无效导致释放JFR失败
* 故障编号：urma_836
* 故障现象：
    * 关键日志：匹配`urma_advise_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于释放JFR，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_advise_jfr
#### 9.128 URMA context、设备对象、JFS对象无效导致执行JFR失败
* 故障编号：urma_837
* 故障现象：
    * 关键日志：匹配`urma_advise_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行JFR，调用方传入的URMA context、设备对象、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_advise_jfr
#### 9.129 URMA context、设备对象、provider操作表、JFS对象无效导致执行JFR失败
* 故障编号：urma_838
* 故障现象：
    * 关键日志：匹配`urma_advise_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行JFR，调用方传入的URMA context、设备对象、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_advise_jfr
#### 9.130 URMA context、provider操作表、JFS对象无效导致执行JFR失败
* 故障编号：urma_839
* 故障现象：
    * 关键日志：匹配`urma_unadvise_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行JFR，调用方传入的URMA context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unadvise_jfr
#### 9.131 URMA context、设备对象、JFS对象无效导致执行JFR失败
* 故障编号：urma_840
* 故障现象：
    * 关键日志：匹配`urma_unadvise_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行JFR，调用方传入的URMA context、设备对象、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unadvise_jfr
#### 9.132 URMA context、设备对象、provider操作表、JFS对象无效导致执行JFR失败
* 故障编号：urma_841
* 故障现象：
    * 关键日志：匹配`urma_unadvise_jfr`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行JFR，调用方传入的URMA context、设备对象、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_unadvise_jfr
#### 9.133 URMA context、provider操作表、JFS对象无效导致执行JFR失败
* 故障编号：urma_842
* 故障现象：
    * 关键日志：匹配`urma_advise_jfr_async`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行JFR，调用方传入的URMA context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_advise_jfr_async
#### 9.134 URMA context、设备对象、JFS对象无效导致执行JFR失败
* 故障编号：urma_843
* 故障现象：
    * 关键日志：匹配`urma_advise_jfr_async`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行JFR，调用方传入的URMA context、设备对象、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_advise_jfr_async
#### 9.135 URMA context、设备对象、provider操作表、JFS对象无效导致执行JFR失败
* 故障编号：urma_844
* 故障现象：
    * 关键日志：匹配`urma_advise_jfr_async`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行JFR，调用方传入的URMA context、设备对象、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_advise_jfr_async
#### 9.136 URMA context、provider操作表无效导致确认context失败
* 故障编号：urma_845
* 故障现象：
    * 关键日志：匹配`urma_ack_async_event`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于确认context，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_ack_async_event
#### 9.137 URMA context、provider操作表无效导致确认context失败
* 故障编号：urma_846
* 故障现象：
    * 关键日志：匹配`urma_ack_async_event`，匹配`Invalid parameter with ops nullptr.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于确认context，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_ack_async_event
#### 9.138 URMA context、provider操作表无效导致确认context失败
* 故障编号：urma_847
* 故障现象：
    * 关键日志：匹配`urma_user_ctl`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于确认context，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_user_ctl
#### 9.139 URMA context、provider操作表、provider未提供user_ctl操作实现无效导致执行context失败
* 故障编号：urma_848
* 故障现象：
    * 关键日志：匹配`urma_user_ctl`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行context，调用方传入的URMA context、provider操作表、provider未提供user_ctl操作实现不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_user_ctl
#### 9.140 执行context过程中依赖步骤失败
* 故障编号：urma_849
* 故障现象：
    * 关键日志：匹配`urma_user_ctl`，匹配`Failed to excecute user_ctl, ret:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_user_ctl
#### 9.141 分配设备过程中依赖步骤失败
* 故障编号：urma_850
* 故障现象：
    * 关键日志：匹配`urma_match_driver`，匹配`snprintf failed`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于分配设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_match_driver
#### 9.142 执行context过程中依赖步骤失败
* 故障编号：urma_851
* 故障现象：
    * 关键日志：匹配`check_valid_sgl`，匹配`sge is a null pointer.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：check_valid_sgl
#### 9.143 执行JFC所需输入对象无效导致轮询JFC失败
* 故障编号：urma_852
* 故障现象：
    * 关键日志：匹配`urma_rearm_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于轮询JFC，调用方传入的执行JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_rearm_jfc
#### 9.144 等待JFC所需输入对象无效导致等待JFC失败
* 故障编号：urma_853
* 故障现象：
    * 关键日志：匹配`urma_wait_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于等待JFC，调用方传入的等待JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_wait_jfc
#### 9.145 确认JFC所需输入对象无效导致确认JFC失败
* 故障编号：urma_854
* 故障现象：
    * 关键日志：匹配`urma_ack_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于确认JFC，调用方传入的确认JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_ack_jfc
#### 9.146 确认JFC所需输入对象无效导致确认JFC失败
* 故障编号：urma_855
* 故障现象：
    * 关键日志：匹配`urma_ack_jfc`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于确认JFC，调用方传入的确认JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_ack_jfc
#### 9.147 执行EID所需输入对象无效导致执行EID失败
* 故障编号：urma_856
* 故障现象：
    * 关键日志：匹配`urma_str_to_eid`，匹配`Invalid argument.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行EID，调用方传入的执行EID所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_str_to_eid
#### 9.148 执行EID过程中依赖步骤失败
* 故障编号：urma_857
* 故障现象：
    * 关键日志：匹配`urma_str_to_eid`，匹配`format error:`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于执行EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_str_to_eid
#### 9.149 执行URMA资源所需输入对象无效导致获取URMA资源失败
* 故障编号：urma_858
* 故障现象：
    * 关键日志：匹配`urma_getenv_log_level`，匹配`Invalid parameter: log level str.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于获取URMA资源，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_getenv_log_level
#### 9.150 provider操作表无效导致注销URMA资源失败
* 故障编号：urma_859
* 故障现象：
    * 关键日志：匹配`urma_validate_driver`，匹配`Invalid driver name length.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于注销URMA资源，调用方传入的provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_validate_driver
#### 9.151 打开URMA资源过程中依赖步骤失败
* 故障编号：urma_860
* 故障现象：
    * 关键日志：匹配`urma_open_drivers`，匹配`Failed to prepare dli_fname.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于打开URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_open_drivers
#### 9.152 设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败
* 故障编号：urma_861
* 故障现象：
    * 关键日志：匹配`urma_open_drivers`，匹配`Failed to open liburma dir`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始化。
* 解决办法：无
* 函数名：urma_open_drivers
#### 9.153 打开URMA资源过程中依赖步骤失败
* 故障编号：urma_862
* 故障现象：
    * 关键日志：匹配`urma_open_drivers`，匹配`snprintf_s`，匹配`failed`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于打开URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。
* 解决办法：无
* 函数名：urma_open_drivers
#### 9.154 URMA context、设备对象、provider操作表无效导致设置context失败
* 故障编号：urma_863
* 故障现象：
    * 关键日志：匹配`urma_set_context_opt`，匹配`Invalid parameter.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置context，调用方传入的URMA context、设备对象、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_context_opt
#### 9.155 URMA context、设备对象、provider操作表无效导致设置context失败
* 故障编号：urma_864
* 故障现象：
    * 关键日志：匹配`urma_set_context_opt`，匹配`Invalid option value.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置context，调用方传入的URMA context、设备对象、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_context_opt
#### 9.156 URMA context、设备对象、provider操作表无效导致设置context失败
* 故障编号：urma_865
* 故障现象：
    * 关键日志：匹配`urma_set_context_opt`，匹配`Invalid option value len.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置context，调用方传入的URMA context、设备对象、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_context_opt
#### 9.157 URMA context无效导致设置context失败
* 故障编号：urma_866
* 故障现象：
    * 关键日志：匹配`urma_set_context_opt`，匹配`Invalid option name.`
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：函数用于设置context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。
* 解决办法：无
* 函数名：urma_set_context_opt
