## URMA故障
### 1 初始化失败
* 故障编号：urma_001
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 1.1 urma_provider_bond_init 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_002
* 故障现象：
    * 关键日志：匹配 Provider Bond register ops failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_provider_bond_init 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 1.2 urma_register_log_func 校验 URMA 对象 无效导致注册流程拒绝继续执行
* 故障编号：urma_003
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_register_log_func 在执行注册前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：当前不会触发失败
#### 1.3 urma_register_provider_ops 校验 provider 无效导致注册流程拒绝继续执行
* 故障编号：urma_004
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_register_provider_ops 在执行注册前发现调用方传入的 provider 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 1.4 urma_unregister_provider_ops 校验 provider 无效导致注册流程拒绝继续执行
* 故障编号：urma_005
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unregister_provider_ops 在执行注册前发现调用方传入的 provider 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 1.5 urma_init 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_006
* 故障现象：
    * 关键日志：匹配 urma_init has been called before
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_init 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：查看 `/usr/lib64/urma` 目录下是否存在 `liburma_udma.so` 等驱动文件，确认文件具备执行权限，完成正确部署后重试
#### 1.6 urma_init 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_007
* 故障现象：
    * 关键日志：匹配 None of the providers registered
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_init 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：查看 `/usr/lib64/urma` 目录下是否存在 `liburma_udma.so` 等驱动文件，确认文件具备执行权限，完成正确部署后重试
### 2 建链失败
* 故障编号：urma_008
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 2.1 bondp_create_jfc 执行创建 设备 失败导致当前资源状态无法推进
* 故障编号：urma_009
* 故障现象：
    * 关键日志：依次匹配 `Failed to create bondp comp, dev_name:`、`, eid_idx:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jfc 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.2 bondp_create_jfc 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_010
* 故障现象：
    * 关键日志：依次匹配 `Failed to create vjfc, dev_name:`、`, eid_idx:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jfc 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.3 bondp_import_jetty 执行导入 context 失败导致当前资源状态无法推进
* 故障编号：urma_011
* 故障现象：
    * 关键日志：依次匹配 `Failed to import vjetty, [`、`]:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_jetty 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.4 bondp_import_jetty 校验 Jetty 业务条件不满足导致导入流程拒绝继续执行
* 故障编号：urma_012
* 故障现象：
    * 关键日志：匹配 `Multi-path jetty only support CTP, tp_type:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_jetty 在执行导入时发现 Jetty 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 2.5 bondp_import_jetty 校验 Jetty 业务条件不满足导致导入流程拒绝继续执行
* 故障编号：urma_013
* 故障现象：
    * 关键日志：匹配 `Multi-path jetty only support RM or RC, trans_mode:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_jetty 在执行导入时发现 Jetty 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 2.6 bondp_import_jetty 校验 Jetty 业务条件不满足导致导入流程拒绝继续执行
* 故障编号：urma_014
* 故障现象：
    * 关键日志：匹配 `Single-path jetty only support UTP or RTP, tp_type:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_jetty 在执行导入时发现 Jetty 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 2.7 bondp_import_jetty 校验 Jetty 业务条件不满足导致导入流程拒绝继续执行
* 故障编号：urma_015
* 故障现象：
    * 关键日志：匹配 `Single-path jetty only support RC, trans_mode:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_jetty 在执行导入时发现 Jetty 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 2.8 bondp_import_jetty 执行导入 context 失败导致当前资源状态无法推进
* 故障编号：urma_016
* 故障现象：
    * 关键日志：匹配 Failed to import pjetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_jetty 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.9 bind_jetty_single_path 校验 Jetty 业务条件不满足导致绑定流程拒绝继续执行
* 故障编号：urma_017
* 故障现象：
    * 关键日志：匹配 No valid direct route
    * 日志路径：URMA_LOG_PATH
* 故障原因：bind_jetty_single_path 在执行绑定时发现 Jetty 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 2.10 bondp_bind_jetty 校验 Jetty 无效导致绑定流程拒绝继续执行
* 故障编号：urma_018
* 故障现象：
    * 关键日志：匹配 Invalid param jetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_bind_jetty 在执行绑定前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.11 bondp_bind_jetty 校验 Jetty 业务条件不满足导致绑定流程拒绝继续执行
* 故障编号：urma_019
* 故障现象：
    * 关键日志：匹配 Jetty already has a binded target jetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_bind_jetty 在执行绑定时发现 Jetty 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 2.12 bondp_bind_jetty 校验 context 业务条件不满足导致绑定流程拒绝继续执行
* 故障编号：urma_020
* 故障现象：
    * 关键日志：匹配 The is_multipath attributes of jetty and tjetty are different
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_bind_jetty 在执行绑定时发现 context 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 2.13 bondp_unbind_jetty 校验 Jetty 无效导致绑定流程拒绝继续执行
* 故障编号：urma_021
* 故障现象：
    * 关键日志：匹配 Invalid param jetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_unbind_jetty 在执行绑定前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.14 bondp_unbind_jetty 执行绑定 目标 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_022
* 故障现象：
    * 关键日志：依次匹配 `Failed to unbind tjetty [`、`](`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_unbind_jetty 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.15 import_jfr_default 校验 JFR 业务条件不满足导致导入流程拒绝继续执行
* 故障编号：urma_023
* 故障现象：
    * 关键日志：匹配 Failed to import jfr, no valid route to rjfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：import_jfr_default 在执行导入时发现 JFR 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 2.16 get_new_jfs_wr 执行获取 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_024
* 故障现象：
    * 关键日志：匹配 `unsupport opcode`
    * 日志路径：URMA_LOG_PATH
* 故障原因：get_new_jfs_wr 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.17 bondp_global_ctx_init 分配 context 临时参数失败导致初始化流程无法继续
* 故障编号：urma_025
* 故障现象：
    * 关键日志：匹配 Failed to alloc global context
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_global_ctx_init 需要为 context 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 2.18 get_bonding_eid_by_target_eid 校验 EID 无效导致获取流程拒绝继续执行
* 故障编号：urma_026
* 故障现象：
    * 关键日志：匹配 Invalid param
    * 日志路径：URMA_LOG_PATH
* 故障原因：get_bonding_eid_by_target_eid 在执行获取前发现调用方传入的 EID 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.19 urma_cmd_create_jfs 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_027
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_jfs 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.20 urma_cmd_set_jfs_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_028
* 故障现象：
    * 关键日志：匹配 jfc not exist in jfs
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jfs_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFS 状态。
* 解决办法：无
#### 2.21 urma_cmd_set_jfs_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_029
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_set_jfs_opt, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jfs_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFS 状态。
* 解决办法：无
#### 2.22 urma_cmd_get_jfs_opt 校验 JFS 无效导致获取流程拒绝继续执行
* 故障编号：urma_030
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfs_opt 在执行获取前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.23 urma_cmd_get_jfs_opt 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_031
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfs_opt 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.24 urma_cmd_get_jfs_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_032
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_get_jfs_opt, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfs_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFS 状态。
* 解决办法：无
#### 2.25 urma_cmd_get_jfs_opt 校验 JFS 无效导致获取流程拒绝继续执行
* 故障编号：urma_033
* 故障现象：
    * 关键日志：匹配 Invalid out buffer from kernel
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfs_opt 在执行获取前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.26 urma_cmd_get_jfs_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_034
* 故障现象：
    * 关键日志：依次匹配 `output length too large, out.len=`、`, buf.len=`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfs_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFS 状态。
* 解决办法：无
#### 2.27 urma_cmd_active_jfs 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_035
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_active_jfs 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.28 urma_cmd_active_jfs URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_036
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_active_jfs, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_active_jfs 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFS 状态。
* 解决办法：无
#### 2.29 urma_cmd_deactive_jfs 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_037
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_deactive_jfs 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.30 urma_cmd_deactive_jfs URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_038
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_deactive_jfs, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_deactive_jfs 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFS 状态。
* 解决办法：无
#### 2.31 urma_cmd_get_jfc_opt 校验 JFC 无效导致获取流程拒绝继续执行
* 故障编号：urma_039
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfc_opt 在执行获取前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.32 urma_cmd_get_jfc_opt 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_040
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfc_opt 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.33 urma_cmd_get_jfc_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_041
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_get_jfc_opt, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfc_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。
* 解决办法：无
#### 2.34 urma_cmd_get_jfc_opt 校验 JFC 无效导致获取流程拒绝继续执行
* 故障编号：urma_042
* 故障现象：
    * 关键日志：匹配 Invalid out buffer from kernel
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfc_opt 在执行获取前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.35 urma_cmd_get_jfc_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_043
* 故障现象：
    * 关键日志：依次匹配 `output length too large, out.len=`、`, buf.len=`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfc_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。
* 解决办法：无
#### 2.36 urma_cmd_active_jfc 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_044
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_active_jfc 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.37 urma_cmd_active_jfc URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_045
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_active_jfc, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_active_jfc 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。
* 解决办法：无
#### 2.38 urma_cmd_deactive_jfc 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_046
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_deactive_jfc 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.39 urma_cmd_deactive_jfc URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_047
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_active_jfc, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_deactive_jfc 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。
* 解决办法：无
#### 2.40 urma_cmd_create_jfce URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_048
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_create_jfce, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_jfce 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFCE 状态。
* 解决办法：无
#### 2.41 urma_cmd_import_jfr 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_049
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_import_jfr 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.42 urma_cmd_import_jfr_ex 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_050
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_import_jfr_ex 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.43 urma_cmd_set_jfr_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_051
* 故障现象：
    * 关键日志：匹配 jfc not exist in jfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jfr_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFR 状态。
* 解决办法：无
#### 2.44 urma_cmd_set_jfr_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_052
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_set_jfr_opt, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jfr_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFR 状态。
* 解决办法：无
#### 2.45 urma_cmd_get_jfr_opt 校验 JFR 无效导致获取流程拒绝继续执行
* 故障编号：urma_053
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfr_opt 在执行获取前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.46 urma_cmd_get_jfr_opt 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_054
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfr_opt 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.47 urma_cmd_get_jfr_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_055
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_get_jfr_opt, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfr_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFR 状态。
* 解决办法：无
#### 2.48 urma_cmd_get_jfr_opt 校验 JFR 无效导致获取流程拒绝继续执行
* 故障编号：urma_056
* 故障现象：
    * 关键日志：匹配 Invalid out buffer from kernel
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfr_opt 在执行获取前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.49 urma_cmd_get_jfr_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_057
* 故障现象：
    * 关键日志：依次匹配 `output length too large, out.len=`、`, buf.len=`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jfr_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFR 状态。
* 解决办法：无
#### 2.50 urma_cmd_active_jfr 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_058
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_active_jfr 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.51 urma_cmd_active_jfr URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_059
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_active_jfr, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_active_jfr 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFR 状态。
* 解决办法：无
#### 2.52 urma_cmd_deactive_jfr 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_060
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_deactive_jfr 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.53 urma_cmd_deactive_jfr URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_061
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_deactive_jfr, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_deactive_jfr 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFR 状态。
* 解决办法：无
#### 2.54 urma_cmd_bind_jetty 校验 context 无效导致绑定流程拒绝继续执行
* 故障编号：urma_062
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_bind_jetty 在执行绑定前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.55 urma_cmd_bind_jetty_ex 校验 context 无效导致绑定流程拒绝继续执行
* 故障编号：urma_063
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_bind_jetty_ex 在执行绑定前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.56 urma_cmd_unbind_jetty 校验 context 无效导致绑定流程拒绝继续执行
* 故障编号：urma_064
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_unbind_jetty 在执行绑定前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.57 urma_cmd_import_jetty 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_065
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_import_jetty 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.58 urma_cmd_import_jetty_ex 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_066
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_import_jetty_ex 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.59 urma_cmd_set_jetty_opt 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_067
* 故障现象：
    * 关键日志：匹配 jetty->jetty_cfg.shared.jfc is not exist
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jetty_opt 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 2.60 urma_cmd_set_jetty_opt 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_068
* 故障现象：
    * 关键日志：匹配 jetty->jetty_cfg.shared.jfr is not exist
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jetty_opt 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 2.61 urma_cmd_set_jetty_opt 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_069
* 故障现象：
    * 关键日志：匹配 jetty->jetty_cfg.jetty_grp is not exist
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jetty_opt 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 2.62 urma_cmd_set_jetty_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_070
* 故障现象：
    * 关键日志：匹配 jetty->jetty_cfg.jfs_cfg.jfc is not exist
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jetty_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 Jetty 状态。
* 解决办法：无
#### 2.63 urma_cmd_set_jetty_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_071
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_set_jetty_opt, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jetty_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 Jetty 状态。
* 解决办法：无
#### 2.64 urma_cmd_get_jetty_opt 校验 Jetty 无效导致获取流程拒绝继续执行
* 故障编号：urma_072
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jetty_opt 在执行获取前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.65 urma_cmd_get_jetty_opt 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_073
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jetty_opt 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.66 urma_cmd_get_jetty_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_074
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_get_jetty_opt, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jetty_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 Jetty 状态。
* 解决办法：无
#### 2.67 urma_cmd_get_jetty_opt 校验 Jetty 无效导致获取流程拒绝继续执行
* 故障编号：urma_075
* 故障现象：
    * 关键日志：匹配 Invalid out buffer from kernel
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_jetty_opt 在执行获取前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.68 urma_cmd_active_jetty 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_076
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_active_jetty 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.69 urma_cmd_active_jetty 校验 Jetty 无效导致激活流程拒绝继续执行
* 故障编号：urma_077
* 故障现象：
    * 关键日志：匹配 Invalid flag
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_active_jetty 在执行激活前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.70 urma_cmd_active_jetty URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_078
* 故障现象：
    * 关键日志：匹配 `ioctl failed in urma_cmd_active_jetty, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_active_jetty 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 Jetty 状态。
* 解决办法：无
#### 2.71 urma_cmd_deactive_jetty 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_079
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_deactive_jetty 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.72 urma_cmd_deactive_jetty URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_080
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_deactive_jetty, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_deactive_jetty 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 Jetty 状态。
* 解决办法：无
#### 2.73 urma_cmd_modify_tp 校验 context 无效导致修改流程拒绝继续执行
* 故障编号：urma_081
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_modify_tp 在执行修改前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.74 urma_cmd_query_device_attr 校验 设备 无效导致查询流程拒绝继续执行
* 故障编号：urma_082
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_query_device_attr 在执行查询前发现调用方传入的 设备 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.75 urma_cmd_import_jetty_async 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_083
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_import_jetty_async 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.76 urma_cmd_bind_jetty_async 校验 context 无效导致绑定流程拒绝继续执行
* 故障编号：urma_084
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_bind_jetty_async 在执行绑定前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.77 urma_cmd_unbind_jetty_async 校验 context 无效导致绑定流程拒绝继续执行
* 故障编号：urma_085
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_unbind_jetty_async 在执行绑定前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.78 urma_cmd_get_tp_list 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_086
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_tp_list 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.79 urma_cmd_set_tp_attr 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_087
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_tp_attr 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.80 urma_cmd_set_tp_attr 校验 TP 无效导致设置流程拒绝继续执行
* 故障编号：urma_088
* 故障现象：
    * 关键日志：匹配 Invalid tp_attr bytes
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_tp_attr 在执行设置前发现调用方传入的 TP 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.81 urma_cmd_set_tp_attr URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_089
* 故障现象：
    * 关键日志：匹配 `Failed in ioctl set_tp_attr, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_tp_attr 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 TP 状态。
* 解决办法：无
#### 2.82 urma_cmd_get_tp_attr 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_090
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_tp_attr 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.83 urma_cmd_get_tp_attr 校验 TP 无效导致获取流程拒绝继续执行
* 故障编号：urma_091
* 故障现象：
    * 关键日志：匹配 Invalid tp_attr bytes
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_tp_attr 在执行获取前发现调用方传入的 TP 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.84 urma_cmd_get_tp_attr URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_092
* 故障现象：
    * 关键日志：匹配 `Failed in ioctl get_tp_attr, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_tp_attr 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 TP 状态。
* 解决办法：无
#### 2.85 urma_cmd_exchange_tp_info 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_093
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_exchange_tp_info 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.86 urma_cmd_get_eid_by_ip 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_094
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_eid_by_ip 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.87 urma_tlv_ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_095
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed, ret:`、`, errno:`、`, cmd:`、`, kdrv_err:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_tlv_ioctl URMA内核态调用驱动异常，返回错误码2048，则容器中用户态日志出现ioctl失败，并且errno为特定的2048，故障发生在内核态驱动
* 解决办法：UDMA驱动相关，需进一步排查硬件
#### 2.88 urma_active_jfc 校验 JFC 无效导致激活流程拒绝继续执行
* 故障编号：urma_096
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfc 在执行激活前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.89 urma_active_jfc 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_097
* 故障现象：
    * 关键日志：依次匹配 `jfc cfg depth of range, depth:`、`, max_depth:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfc 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 2.90 urma_active_jfc 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_098
* 故障现象：
    * 关键日志：匹配 Jfc state is wrong in active_jfc
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfc 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 2.91 urma_active_jfc 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_099
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfc 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.92 urma_active_jfc 执行激活 JFC 失败导致当前资源状态无法推进
* 故障编号：urma_100
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->active_jfc
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfc 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.93 urma_deactive_jfc 校验 JFC 无效导致激活流程拒绝继续执行
* 故障编号：urma_101
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jfc 在执行激活前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.94 urma_deactive_jfc 执行激活 JFC 失败导致当前资源状态无法推进
* 故障编号：urma_102
* 故障现象：
    * 关键日志：匹配 Jfc state is wrong in deactive_jfc
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jfc 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.95 urma_deactive_jfc 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_103
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jfc 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.96 urma_deactive_jfc 执行激活 JFC 失败导致当前资源状态无法推进
* 故障编号：urma_104
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->deactive_jfc
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jfc 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.97 urma_active_jfs 校验 JFS 无效导致激活流程拒绝继续执行
* 故障编号：urma_105
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfs 在执行激活前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.98 urma_active_jfs 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_106
* 故障现象：
    * 关键日志：匹配 jfs state is wrong in active_jfs
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfs 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 2.99 urma_active_jfs 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_107
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfs 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.100 urma_active_jfs 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_108
* 故障现象：
    * 关键日志：依次匹配 `jfs cfg out of range, depth:`、`, max_depth:`、`, inline_data:`、`, max_inline_len:`、`, sge:`、`, max_sge:`、`, rsge:`、`, max_rsge:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfs 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 2.101 urma_active_jfs 执行激活 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_109
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->active_jfs
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.102 urma_deactive_jfs 校验 JFS 无效导致激活流程拒绝继续执行
* 故障编号：urma_110
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jfs 在执行激活前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.103 urma_deactive_jfs 执行激活 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_111
* 故障现象：
    * 关键日志：匹配 jfs state is wrong in deactive_jfs
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.104 urma_deactive_jfs 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_112
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jfs 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.105 urma_deactive_jfs 执行激活 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_113
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->deactive_jfs
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.106 urma_import_jfr_compat 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_114
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jfr_compat 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.107 urma_import_jfr_compat 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_115
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jfr_compat 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.108 urma_import_jfr 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_116
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jfr 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：UDMA 错误定界；建链交换信息失败，可重试
#### 2.109 urma_active_jfr 校验 JFR 无效导致激活流程拒绝继续执行
* 故障编号：urma_117
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfr 在执行激活前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.110 urma_active_jfr 校验 JFR 无效导致激活流程拒绝继续执行
* 故障编号：urma_118
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, trans_mode:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfr 在执行激活前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.111 urma_active_jfr 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_119
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfr 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.112 urma_active_jfr 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_120
* 故障现象：
    * 关键日志：依次匹配 `jfr cfg out of range, depth:`、`, max_depth:`、`, sge:`、`, max_sge:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfr 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 2.113 urma_active_jfr 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_121
* 故障现象：
    * 关键日志：匹配 jfr state is wrong in active_jfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfr 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 2.114 urma_active_jfr 执行激活 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_122
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->active_jfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.115 urma_deactive_jfr 校验 JFR 无效导致激活流程拒绝继续执行
* 故障编号：urma_123
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jfr 在执行激活前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.116 urma_deactive_jfr 执行激活 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_124
* 故障现象：
    * 关键日志：匹配 jfr state is wrong in deactive_jfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.117 urma_deactive_jfr 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_125
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jfr 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.118 urma_deactive_jfr 执行激活 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_126
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->deactive_jfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.119 urma_flush_jetty 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_127
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_flush_jetty 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.120 urma_import_jetty_compat 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_128
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jetty_compat 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.121 urma_import_jetty_compat 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_129
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jetty_compat 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.122 urma_import_jetty 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_130
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jetty 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.123 urma_bind_jetty 校验 目标 Jetty 无效导致绑定流程拒绝继续执行
* 故障编号：urma_131
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_bind_jetty 在执行绑定前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.124 urma_bind_jetty 校验 context 无效导致绑定流程拒绝继续执行
* 故障编号：urma_132
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_bind_jetty 在执行绑定前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.125 urma_bind_jetty 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_133
* 故障现象：
    * 关键日志：匹配 Not allowed to bind local jetty: of mode: with remote jetty: of mode
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_bind_jetty 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 2.126 urma_bind_jetty 执行绑定 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_134
* 故障现象：
    * 关键日志：依次匹配 `Not allowed to bind local jetty:`、`of mode:`、`, with remote jetty:`、`of mode:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_bind_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.127 urma_bind_jetty_ex 校验 目标 Jetty 无效导致绑定流程拒绝继续执行
* 故障编号：urma_135
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_bind_jetty_ex 在执行绑定前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.128 urma_bind_jetty_ex 执行绑定 目标 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_136
* 故障现象：
    * 关键日志：匹配 Not allowed to bind local jetty: of mode: with remote jetty: of mode
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_bind_jetty_ex 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.129 urma_bind_jetty_ex 执行绑定 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_137
* 故障现象：
    * 关键日志：依次匹配 `Not allowed to bind local jetty:`、`, with remote jetty:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_bind_jetty_ex 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.130 urma_bind_jetty_ex 校验 context 无效导致绑定流程拒绝继续执行
* 故障编号：urma_138
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_bind_jetty_ex 在执行绑定前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.131 urma_unbind_jetty 校验 Jetty 无效导致绑定流程拒绝继续执行
* 故障编号：urma_139
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unbind_jetty 在执行绑定前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.132 urma_unbind_jetty 执行绑定 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_140
* 故障现象：
    * 关键日志：匹配 Not allowed to call unbind as the tp mode of jetty : is
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unbind_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.133 urma_unbind_jetty 校验 context 无效导致绑定流程拒绝继续执行
* 故障编号：urma_141
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unbind_jetty 在执行绑定前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.134 urma_bind_jetty_async 校验 目标 Jetty 无效导致绑定流程拒绝继续执行
* 故障编号：urma_142
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_bind_jetty_async 在执行绑定前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.135 urma_bind_jetty_async 执行绑定 目标 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_143
* 故障现象：
    * 关键日志：依次匹配 `Not allowed to bind local jetty:`、`of mode:`、`with remote jetty:`、`of mode:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_bind_jetty_async 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.136 urma_bind_jetty_async 执行绑定 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_144
* 故障现象：
    * 关键日志：依次匹配 `Not allowed to bind local jetty:`、`, with remote jetty:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_bind_jetty_async 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.137 urma_bind_jetty_async 校验 context 无效导致绑定流程拒绝继续执行
* 故障编号：urma_145
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_bind_jetty_async 在执行绑定前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.138 urma_unbind_jetty_async 校验 Jetty 无效导致绑定流程拒绝继续执行
* 故障编号：urma_146
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unbind_jetty_async 在执行绑定前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.139 urma_unbind_jetty_async 执行绑定 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_147
* 故障现象：
    * 关键日志：依次匹配 `Not allowed to call unbind as the tp mode of jetty :`、`is:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unbind_jetty_async 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.140 urma_unbind_jetty_async 校验 context 无效导致绑定流程拒绝继续执行
* 故障编号：urma_148
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unbind_jetty_async 在执行绑定前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.141 urma_active_jetty 校验 Jetty 无效导致激活流程拒绝继续执行
* 故障编号：urma_149
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jetty 在执行激活前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.142 urma_active_jetty 校验 Jetty 无效导致激活流程拒绝继续执行
* 故障编号：urma_150
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jetty 在执行激活前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.143 urma_active_jetty 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_151
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jetty 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.144 urma_active_jetty 校验 Jetty 无效导致激活流程拒绝继续执行
* 故障编号：urma_152
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jetty 在执行激活前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.145 urma_active_jetty 执行激活 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_153
* 故障现象：
    * 关键日志：匹配 Jetty state is wrong in active_jetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.146 urma_active_jetty 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_154
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jetty 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.147 urma_active_jetty 执行激活 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_155
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->active_jetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_active_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.148 urma_deactive_jetty 校验 Jetty 无效导致激活流程拒绝继续执行
* 故障编号：urma_156
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jetty 在执行激活前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.149 urma_deactive_jetty 执行激活 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_157
* 故障现象：
    * 关键日志：匹配 Jetty state is wrong in deactive_jetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.150 urma_deactive_jetty 校验 context 无效导致激活流程拒绝继续执行
* 故障编号：urma_158
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jetty 在执行激活前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.151 urma_deactive_jetty 执行激活 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_159
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->deactive_jetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_deactive_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 2.152 urma_get_tpn 校验 Jetty 无效导致获取流程拒绝继续执行
* 故障编号：urma_160
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_tpn 在执行获取前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.153 urma_get_tpn 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_161
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_tpn 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.154 urma_get_net_addr_list 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_162
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_net_addr_list 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.155 urma_free_net_addr_list 校验 URMA 对象 无效导致释放流程拒绝继续执行
* 故障编号：urma_163
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_net_addr_list 在执行释放前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.156 urma_modify_tp 校验 context 无效导致修改流程拒绝继续执行
* 故障编号：urma_164
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_modify_tp 在执行修改前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.157 urma_modify_tp 校验 context 无效导致修改流程拒绝继续执行
* 故障编号：urma_165
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_modify_tp 在执行修改前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.158 urma_get_tp_list 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_166
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_tp_list 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.159 urma_get_tp_list 校验 TP 无效导致获取流程拒绝继续执行
* 故障编号：urma_167
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, trans_mode:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_tp_list 在执行获取前发现调用方传入的 TP 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.160 urma_get_tp_list 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_168
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_tp_list 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.161 urma_set_tp_attr 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_169
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_tp_attr 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.162 urma_set_tp_attr 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_170
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_tp_attr 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.163 urma_get_tp_attr 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_171
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_tp_attr 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.164 urma_get_tp_attr 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_172
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_tp_attr 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.165 urma_get_eid_by_ip 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_173
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_eid_by_ip 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 2.166 urma_get_eid_by_ip 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_174
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_eid_by_ip 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
### 3 资源创建失败
* 故障编号：urma_175
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 3.1 bondp_create_jfce 执行创建 JFCE 失败导致当前资源状态无法推进
* 故障编号：urma_176
* 故障现象：
    * 关键日志：匹配 Failed to create bonding jfce
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jfce 调用下层 provider、bond 组件或系统接口处理 JFCE 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.2 bondp_create_vjfs 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_177
* 故障现象：
    * 关键日志：匹配 ubcore create jfs failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_vjfs 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.3 bondp_create_pjfs 执行创建 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_178
* 故障现象：
    * 关键日志：匹配 Failed to create pjfs
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_pjfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.4 bondp_create_jfs 执行创建 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_179
* 故障现象：
    * 关键日志：匹配 In matrix server, JFS don't support single-path mode
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.5 bondp_create_jfs 执行创建 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_180
* 故障现象：
    * 关键日志：匹配 Failed to create bondp comp
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.6 bondp_create_jfs 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_181
* 故障现象：
    * 关键日志：匹配 Failed to create pjfs
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jfs 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.7 bondp_create_jfs 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_182
* 故障现象：
    * 关键日志：匹配 Failed to create vjfs
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jfs 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.8 bondp_create_jfs 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_183
* 故障现象：
    * 关键日志：匹配 Failed to add jfs p_vjetty_id info
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jfs 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.9 bondp_create_jfs 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_184
* 故障现象：
    * 关键日志：匹配 Failed to create jfs datapath ctx
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jfs 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.10 bondp_create_vjfr 执行创建 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_185
* 故障现象：
    * 关键日志：匹配 bondp init jfr fail
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_vjfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.11 bondp_create_pjfr 校验 JFR 无效导致创建流程拒绝继续执行
* 故障编号：urma_186
* 故障现象：
    * 关键日志：匹配 Invalid param jfc
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_pjfr 在执行创建前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.12 bondp_create_pjfr 执行创建 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_187
* 故障现象：
    * 关键日志：匹配 Failed to create pjfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_pjfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.13 bondp_create_jfr 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_188
* 故障现象：
    * 关键日志：匹配 Failed to create pjfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jfr 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.14 bondp_create_jfr 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_189
* 故障现象：
    * 关键日志：匹配 Failed to create vjfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jfr 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.15 bondp_create_jfr 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_190
* 故障现象：
    * 关键日志：匹配 Failed to create jfr datapath ctx
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jfr 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.16 bondp_create_pjetty 执行创建 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_191
* 故障现象：
    * 关键日志：匹配 Failed to create pjetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_pjetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.17 bondp_create_jetty 执行创建 设备 失败导致当前资源状态无法推进
* 故障编号：urma_192
* 故障现象：
    * 关键日志：匹配 UB device must use shared jfr when create jetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jetty 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.18 bondp_create_jetty 校验 Jetty 无效导致创建流程拒绝继续执行
* 故障编号：urma_193
* 故障现象：
    * 关键日志：依次匹配 `Invalid well known jetty id:`、`, should be in (0, 1024)`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jetty 在执行创建前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.19 bondp_create_jetty 校验 Jetty 业务条件不满足导致创建流程拒绝继续执行
* 故障编号：urma_194
* 故障现象：
    * 关键日志：匹配 In matrix server, jetty only supports single-path mode with RC
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jetty 在执行创建时发现 Jetty 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 3.20 bondp_create_jetty 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_195
* 故障现象：
    * 关键日志：匹配 In matrix server, multi-device mode don't support single path currently
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jetty 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.21 bondp_create_jetty 执行创建 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_196
* 故障现象：
    * 关键日志：匹配 Failed to create bondp comp
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.22 bondp_create_jetty 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_197
* 故障现象：
    * 关键日志：匹配 Failed to create pjetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jetty 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.23 bondp_create_jetty 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_198
* 故障现象：
    * 关键日志：匹配 Failed to create vjetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jetty 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.24 bondp_create_jetty 更新 context 映射结构失败导致资源索引不可用
* 故障编号：urma_199
* 故障现象：
    * 关键日志：匹配 Failed to add jetty id to p_vjetty_id table
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jetty 需要维护 context 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 3.25 bondp_create_jetty 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_200
* 故障现象：
    * 关键日志：匹配 Failed to create jetty ctx
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_jetty 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.26 bondp_import_jetty 分配 目标 Jetty 临时参数失败导致导入流程无法继续
* 故障编号：urma_201
* 故障现象：
    * 关键日志：匹配 Failed to alloc target jetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_jetty 需要为 目标 Jetty 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.27 bondp_import_jfr 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_202
* 故障现象：
    * 关键日志：匹配 Invalid param ctx
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_jfr 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.28 bondp_import_jfr 分配 目标 Jetty 临时参数失败导致导入流程无法继续
* 故障编号：urma_203
* 故障现象：
    * 关键日志：匹配 Failed to alloc target jetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_jfr 需要为 目标 Jetty 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.29 bondp_import_jfr 执行导入 context 失败导致当前资源状态无法推进
* 故障编号：urma_204
* 故障现象：
    * 关键日志：依次匹配 `Failed to import vjetty, [`、`]:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_jfr 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.30 bdp_vjfce_info_table_add 更新 JFCE 映射结构失败导致资源索引不可用
* 故障编号：urma_205
* 故障现象：
    * 关键日志：匹配 exist node in map
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_vjfce_info_table_add 需要维护 JFCE 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 3.31 bondp_jfce_get_args_list 分配 JFCE 临时参数失败导致获取流程无法继续
* 故障编号：urma_206
* 故障现象：
    * 关键日志：匹配 Failed to alloc jfce args
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_jfce_get_args_list 需要为 JFCE 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.32 bondp_jfce_init_comp_attr_not_single_die 管理 epoll fd 失败导致 JFCE 事件聚合不可用
* 故障编号：urma_207
* 故障现象：
    * 关键日志：匹配 Fail to create epoll_fd
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_jfce_init_comp_attr_not_single_die 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll 系统调用失败，完成事件无法被统一监听和分发。
* 解决办法：无
#### 3.33 bondp_jfce_init_comp_attr_not_single_die 管理 epoll fd 失败导致 JFCE 事件聚合不可用
* 故障编号：urma_208
* 故障现象：
    * 关键日志：匹配 Fail to create hash table
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_jfce_init_comp_attr_not_single_die 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll 系统调用失败，完成事件无法被统一监听和分发。
* 解决办法：无
#### 3.34 bondp_jfc_get_args_list 分配 JFC 临时参数失败导致获取流程无法继续
* 故障编号：urma_209
* 故障现象：
    * 关键日志：匹配 Failed to alloc args
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_jfc_get_args_list 需要为 JFC 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.35 bondp_jfs_get_args_list 分配 JFS 临时参数失败导致获取流程无法继续
* 故障编号：urma_210
* 故障现象：
    * 关键日志：匹配 Failed to alloc args
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_jfs_get_args_list 需要为 JFS 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.36 bondp_jfr_get_args_list 校验 JFR 无效导致获取流程拒绝继续执行
* 故障编号：urma_211
* 故障现象：
    * 关键日志：匹配 Invalid param jfc
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_jfr_get_args_list 在执行获取前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.37 bondp_jfr_get_args_list 分配 JFR 临时参数失败导致获取流程无法继续
* 故障编号：urma_212
* 故障现象：
    * 关键日志：匹配 Failed to alloc args
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_jfr_get_args_list 需要为 JFR 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.38 bondp_jetty_get_args_list 分配 Jetty 临时参数失败导致获取流程无法继续
* 故障编号：urma_213
* 故障现象：
    * 关键日志：匹配 Failed to alloc args
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_jetty_get_args_list 需要为 Jetty 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.39 bondp_segment_get_args_list 校验 segment 无效导致获取流程拒绝继续执行
* 故障编号：urma_214
* 故障现象：
    * 关键日志：匹配 Invalid param va
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_segment_get_args_list 在执行获取前发现调用方传入的 segment 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.40 bondp_segment_get_args_list 分配 segment 临时参数失败导致获取流程无法继续
* 故障编号：urma_215
* 故障现象：
    * 关键日志：匹配 Failed to alloc args
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_segment_get_args_list 需要为 segment 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.41 bondp_segment_uninit_comp_attr 校验 segment 无效导致初始化流程拒绝继续执行
* 故障编号：urma_216
* 故障现象：
    * 关键日志：匹配 invalid param
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_segment_uninit_comp_attr 在执行初始化前发现调用方传入的 segment 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.42 bondp_segment_uninit_comp_attr 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_217
* 故障现象：
    * 关键日志：依次匹配 `Failed to unregister segment, token_id:`、`, handle:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_segment_uninit_comp_attr 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.43 bondp_create_comp 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_218
* 故障现象：
    * 关键日志：匹配 Invalid param ctx
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_comp 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.44 bondp_create_comp 执行创建 URMA 对象 失败导致当前资源状态无法推进
* 故障编号：urma_219
* 故障现象：
    * 关键日志：匹配 `Failed to get args list, type:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_comp 调用下层 provider、bond 组件或系统接口处理 URMA 对象 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.45 bondp_create_comp 执行创建 URMA 对象 失败导致当前资源状态无法推进
* 故障编号：urma_220
* 故障现象：
    * 关键日志：依次匹配 `Failed to create comp`、`, type:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_comp 调用下层 provider、bond 组件或系统接口处理 URMA 对象 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.46 bdp_v_conn_init 更新 映射表 映射结构失败导致资源索引不可用
* 故障编号：urma_221
* 故障现象：
    * 关键日志：匹配 Failed to init slide window in bdp_v_conn_table_add
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_v_conn_init 需要维护 映射表 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 3.47 bdp_v_conn_init 更新 映射表 映射结构失败导致资源索引不可用
* 故障编号：urma_222
* 故障现象：
    * 关键日志：匹配 Failed to init sender slide window in bdp_v_conn_table_add
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_v_conn_init 需要维护 映射表 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 3.48 set_write_wr_ptseg_ptjetty 执行设置 目标 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_223
* 故障现象：
    * 关键日志：匹配 tjetty in WR is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_write_wr_ptseg_ptjetty 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.49 set_write_wr_ptseg_ptjetty 校验 目标 Jetty 无效导致设置流程拒绝继续执行
* 故障编号：urma_224
* 故障现象：
    * 关键日志：匹配 Invalid vtjetty, the structure may be self-consturcted
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_write_wr_ptseg_ptjetty 在执行设置前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.50 set_write_wr_ptseg_ptjetty 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_225
* 故障现象：
    * 关键日志：匹配 Failed to set ptseg, vtseg is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_write_wr_ptseg_ptjetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.51 set_write_wr_ptseg_ptjetty 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_226
* 故障现象：
    * 关键日志：匹配 Write sge.dst->handle is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_write_wr_ptseg_ptjetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.52 set_write_wr_ptseg_ptjetty 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_227
* 故障现象：
    * 关键日志：匹配 bondp_find_vtseg_by_va fail
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_write_wr_ptseg_ptjetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.53 set_write_wr_ptseg_ptjetty 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_228
* 故障现象：
    * 关键日志：匹配 Failed to set ptseg, vtseg is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_write_wr_ptseg_ptjetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.54 set_write_wr_ptseg_ptjetty 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_229
* 故障现象：
    * 关键日志：匹配 Write sge.dst->handle is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_write_wr_ptseg_ptjetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.55 set_write_wr_ptseg_ptjetty 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_230
* 故障现象：
    * 关键日志：匹配 bondp_find_vtseg_by_va fail
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_write_wr_ptseg_ptjetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.56 set_cas_wr_ptseg_pjetty 执行设置 目标 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_231
* 故障现象：
    * 关键日志：匹配 tjetty in WR is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_cas_wr_ptseg_pjetty 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.57 set_cas_wr_ptseg_pjetty 校验 目标 Jetty 无效导致设置流程拒绝继续执行
* 故障编号：urma_232
* 故障现象：
    * 关键日志：匹配 Invalid vtjetty, the structure may be self-consturcted
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_cas_wr_ptseg_pjetty 在执行设置前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.58 set_cas_wr_ptseg_pjetty 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_233
* 故障现象：
    * 关键日志：匹配 when set cas_wr, one of src or dst is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_cas_wr_ptseg_pjetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.59 set_cas_wr_ptseg_pjetty 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_234
* 故障现象：
    * 关键日志：匹配 Failed to set ptseg, vtseg is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_cas_wr_ptseg_pjetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.60 set_cas_wr_ptseg_pjetty 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_235
* 故障现象：
    * 关键日志：匹配 Failed to set ptseg, vtseg is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_cas_wr_ptseg_pjetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.61 set_fadd_wr_ptseg_pjetty 执行设置 目标 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_236
* 故障现象：
    * 关键日志：匹配 tjetty in WR is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_fadd_wr_ptseg_pjetty 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.62 set_fadd_wr_ptseg_pjetty 校验 目标 Jetty 无效导致设置流程拒绝继续执行
* 故障编号：urma_237
* 故障现象：
    * 关键日志：匹配 Invalid vtjetty, the structure may be self-consturcted
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_fadd_wr_ptseg_pjetty 在执行设置前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.63 set_fadd_wr_ptseg_pjetty 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_238
* 故障现象：
    * 关键日志：匹配 when set faa_wr, one of src or dst is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_fadd_wr_ptseg_pjetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.64 set_fadd_wr_ptseg_pjetty 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_239
* 故障现象：
    * 关键日志：匹配 Failed to set ptseg, vtseg is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_fadd_wr_ptseg_pjetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.65 set_fadd_wr_ptseg_pjetty 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_240
* 故障现象：
    * 关键日志：匹配 Failed to set ptseg, vtseg is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_fadd_wr_ptseg_pjetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.66 set_jfs_wr_ptseg_ptjetty 执行设置 目标 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_241
* 故障现象：
    * 关键日志：匹配 Unsupported send opcode
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_jfs_wr_ptseg_ptjetty 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.67 set_jfr_wr_ptjetty_ptseg_without_hdr 执行设置 目标 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_242
* 故障现象：
    * 关键日志：依次匹配 `Recv sge[`、`] has NULL tseg`
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_jfr_wr_ptjetty_ptseg_without_hdr 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.68 create_bjetty_ctx 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_243
* 故障现象：
    * 关键日志：匹配 Unaligned hdr_buf_size
    * 日志路径：URMA_LOG_PATH
* 故障原因：create_bjetty_ctx 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.69 urma_provider_bond_uninit 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_244
* 故障现象：
    * 关键日志：匹配 Provider Bond register ops not registered
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_provider_bond_uninit 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.70 bondp_init 校验 context 业务条件不满足导致初始化流程拒绝继续执行
* 故障编号：urma_245
* 故障现象：
    * 关键日志：匹配 Initialized already
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_init 在执行初始化时发现 context 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 3.71 bondp_init 执行初始化 context 失败导致当前资源状态无法推进
* 故障编号：urma_246
* 故障现象：
    * 关键日志：匹配 Failed to create global context
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_init 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.72 bondp_uninit 执行初始化 context 失败导致当前资源状态无法推进
* 故障编号：urma_247
* 故障现象：
    * 关键日志：匹配 Failed to delete global context
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_uninit 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.73 bondp_init_v_ctx 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_248
* 故障现象：
    * 关键日志：匹配 Failed to query eid
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_init_v_ctx 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 3.74 bondp_init_ctx_table 更新 context 映射结构失败导致资源索引不可用
* 故障编号：urma_249
* 故障现象：
    * 关键日志：匹配 Failed to create p_vjetty_id_table
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_init_ctx_table 需要维护 context 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 3.75 bondp_init_ctx_table 更新 context 映射结构失败导致资源索引不可用
* 故障编号：urma_250
* 故障现象：
    * 关键日志：匹配 Failed to create remote_p2v_jetty_id_table
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_init_ctx_table 需要维护 context 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 3.76 bondp_init_ctx_table 更新 context 映射结构失败导致资源索引不可用
* 故障编号：urma_251
* 故障现象：
    * 关键日志：匹配 Failed to create remote_v2p_token_id_table
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_init_ctx_table 需要维护 context 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 3.77 set_fd_noblock 执行设置 fd 失败导致当前资源状态无法推进
* 故障编号：urma_252
* 故障现象：
    * 关键日志：匹配 `flags:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_fd_noblock 调用下层 provider、bond 组件或系统接口处理 fd 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.78 set_fd_noblock 管理 epoll fd 失败导致 JFCE 事件聚合不可用
* 故障编号：urma_253
* 故障现象：
    * 关键日志：匹配 `ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_fd_noblock 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll 系统调用失败，完成事件无法被统一监听和分发。
* 解决办法：无
#### 3.79 init_slave_context_fd 管理 epoll fd 失败导致 JFCE 事件聚合不可用
* 故障编号：urma_254
* 故障现象：
    * 关键日志：依次匹配 `failed to add fd:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：init_slave_context_fd 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll 系统调用失败，完成事件无法被统一监听和分发。
* 解决办法：无
#### 3.80 init_general_slave_devices 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_255
* 故障现象：
    * 关键日志：匹配 Failed to get slave device info
    * 日志路径：URMA_LOG_PATH
* 故障原因：init_general_slave_devices 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.81 init_general_slave_devices 校验 设备 无效导致初始化流程拒绝继续执行
* 故障编号：urma_256
* 故障现象：
    * 关键日志：匹配 Invalid slave device number of device
    * 日志路径：URMA_LOG_PATH
* 故障原因：init_general_slave_devices 在执行初始化前发现调用方传入的 设备 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.82 init_general_slave_devices 执行初始化 context 失败导致当前资源状态无法推进
* 故障编号：urma_257
* 故障现象：
    * 关键日志：匹配 Failed to create dev ctx in bonding
    * 日志路径：URMA_LOG_PATH
* 故障原因：init_general_slave_devices 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.83 init_matrix_slave_devices 执行初始化 设备 失败导致当前资源状态无法推进
* 故障编号：urma_258
* 故障现象：
    * 关键日志：匹配 urma get device list failed!
    * 日志路径：URMA_LOG_PATH
* 故障原因：init_matrix_slave_devices 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.84 init_matrix_slave_devices 执行初始化 设备 失败导致当前资源状态无法推进
* 故障编号：urma_259
* 故障现象：
    * 关键日志：匹配 Failed to get topo info by bonding eid
    * 日志路径：URMA_LOG_PATH
* 故障原因：init_matrix_slave_devices 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.85 init_matrix_slave_devices 执行初始化 设备 失败导致当前资源状态无法推进
* 故障编号：urma_260
* 故障现象：
    * 关键日志：匹配 Primary eid is empty
    * 日志路径：URMA_LOG_PATH
* 故障原因：init_matrix_slave_devices 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.86 init_matrix_slave_devices 执行初始化 设备 失败导致当前资源状态无法推进
* 故障编号：urma_261
* 故障现象：
    * 关键日志：匹配 No port eid valid
    * 日志路径：URMA_LOG_PATH
* 故障原因：init_matrix_slave_devices 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.87 init_matrix_slave_devices 执行初始化 context 失败导致当前资源状态无法推进
* 故障编号：urma_262
* 故障现象：
    * 关键日志：依次匹配 `Failed to create ctx for primary eid[`、`]`
    * 日志路径：URMA_LOG_PATH
* 故障原因：init_matrix_slave_devices 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.88 bondp_create_context 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_263
* 故障现象：
    * 关键日志：匹配 Uninitialized variables
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_context 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.89 bondp_create_context 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_264
* 故障现象：
    * 关键日志：匹配 Failed to create ctx
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_context 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.90 bondp_create_context 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_265
* 故障现象：
    * 关键日志：匹配 Failed to init v_ctx
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_context 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.91 bondp_create_context 管理 epoll fd 失败导致 JFCE 事件聚合不可用
* 故障编号：urma_266
* 故障现象：
    * 关键日志：匹配 Failed to create context
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_context 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll 系统调用失败，完成事件无法被统一监听和分发。
* 解决办法：无
#### 3.92 bondp_create_context 管理 epoll fd 失败导致 JFCE 事件聚合不可用
* 故障编号：urma_267
* 故障现象：
    * 关键日志：匹配 Failed to create epoll
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_context 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll 系统调用失败，完成事件无法被统一监听和分发。
* 解决办法：无
#### 3.93 bondp_set_aggr_mode 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_268
* 故障现象：
    * 关键日志：匹配 bonding context is invalid in user ctl
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_set_aggr_mode 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.94 bondp_find_vtseg_by_va 更新 目标 segment 映射结构失败导致资源索引不可用
* 故障编号：urma_269
* 故障现象：
    * 关键日志：匹配 bondp_hash_table_lookup fail
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_find_vtseg_by_va 需要维护 目标 segment 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 3.95 bondp_create_pseg 校验 segment 无效导致创建流程拒绝继续执行
* 故障编号：urma_270
* 故障现象：
    * 关键日志：匹配 Invalid segment address for bondp seg
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_pseg 在执行创建前发现调用方传入的 segment 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.96 bondp_create_pseg 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_271
* 故障现象：
    * 关键日志：匹配 Failed to register pseg
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_pseg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.97 bondp_create_vseg 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_272
* 故障现象：
    * 关键日志：匹配 `Fail to register vseg, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_create_vseg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.98 bondp_register_seg 校验 segment 无效导致注册流程拒绝继续执行
* 故障编号：urma_273
* 故障现象：
    * 关键日志：匹配 Invalid token id for register bondp seg
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_register_seg 在执行注册前发现调用方传入的 segment 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.99 bondp_register_seg 分配 segment 临时参数失败导致注册流程无法继续
* 故障编号：urma_274
* 故障现象：
    * 关键日志：匹配 Failed to alloc bondp segment comp
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_register_seg 需要为 segment 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.100 bondp_register_seg 执行注册 context 失败导致当前资源状态无法推进
* 故障编号：urma_275
* 故障现象：
    * 关键日志：匹配 Failed to create pseg
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_register_seg 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.101 bondp_register_seg 执行注册 context 失败导致当前资源状态无法推进
* 故障编号：urma_276
* 故障现象：
    * 关键日志：匹配 Failed to create vseg
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_register_seg 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.102 bondp_import_seg 分配 目标 segment 临时参数失败导致导入流程无法继续
* 故障编号：urma_277
* 故障现象：
    * 关键日志：匹配 Failed to alloc target seg
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_seg 需要为 目标 segment 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.103 bdp_queue_push_tail 校验 URMA 对象 无效导致处理流程拒绝继续执行
* 故障编号：urma_278
* 故障现象：
    * 关键日志：依次匹配 `Failed to enqueue with invalid node_num:`、`, max_node:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_queue_push_tail 在执行处理前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.104 bdp_queue_push_tail 分配 URMA 对象 临时参数失败导致处理流程无法继续
* 故障编号：urma_279
* 故障现象：
    * 关键日志：匹配 Failed to alloc bdp_queue_node
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_queue_push_tail 需要为 URMA 对象 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.105 bdp_slide_wnd_init 校验 URMA 对象 无效导致初始化流程拒绝继续执行
* 故障编号：urma_280
* 故障现象：
    * 关键日志：匹配 Invalid param wnd
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_slide_wnd_init 在执行初始化前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.106 bdp_slide_wnd_init 校验 URMA 对象 无效导致初始化流程拒绝继续执行
* 故障编号：urma_281
* 故障现象：
    * 关键日志：匹配 Invalid param: total_size <= window_size
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_slide_wnd_init 在执行初始化前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.107 bdp_slide_wnd_init 更新 URMA 对象 映射结构失败导致资源索引不可用
* 故障编号：urma_282
* 故障现象：
    * 关键日志：匹配 Failed to init bitmap
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_slide_wnd_init 需要维护 URMA 对象 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 3.108 bdp_slide_wnd_uninit 校验 URMA 对象 无效导致初始化流程拒绝继续执行
* 故障编号：urma_283
* 故障现象：
    * 关键日志：匹配 Invalid param wnd
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_slide_wnd_uninit 在执行初始化前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.109 create_topo_map 校验 拓扑信息 无效导致创建流程拒绝继续执行
* 故障编号：urma_284
* 故障现象：
    * 关键日志：匹配 Invalid topo info to create topo map
    * 日志路径：URMA_LOG_PATH
* 故障原因：create_topo_map 在执行创建前发现调用方传入的 拓扑信息 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.110 create_topo_map 分配 拓扑信息 临时参数失败导致创建流程无法继续
* 故障编号：urma_285
* 故障现象：
    * 关键日志：匹配 Failed to alloc topo_map
    * 日志路径：URMA_LOG_PATH
* 故障原因：create_topo_map 需要为 拓扑信息 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.111 create_topo_map 执行创建 拓扑信息 失败导致当前资源状态无法推进
* 故障编号：urma_286
* 故障现象：
    * 关键日志：匹配 topo info doesn't have cur_node
    * 日志路径：URMA_LOG_PATH
* 故障原因：create_topo_map 调用下层 provider、bond 组件或系统接口处理 拓扑信息 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.112 create_topo_map 更新 EID 映射结构失败导致资源索引不可用
* 故障编号：urma_287
* 故障现象：
    * 关键日志：匹配 Failed to create eid_mapping_hash_table
    * 日志路径：URMA_LOG_PATH
* 故障原因：create_topo_map 需要维护 EID 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 3.113 deepcopy_sge 校验 SGE 无效导致复制流程拒绝继续执行
* 故障编号：urma_288
* 故障现象：
    * 关键日志：匹配 Invalid sge pointer, dst or src is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_sge 在执行复制前发现调用方传入的 SGE 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.114 deepcopy_sg 校验 URMA 对象 无效导致复制流程拒绝继续执行
* 故障编号：urma_289
* 故障现象：
    * 关键日志：匹配 Invalid sg pointer, dst or src is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_sg 在执行复制前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.115 deepcopy_sg 校验 SGE 无效导致复制流程拒绝继续执行
* 故障编号：urma_290
* 故障现象：
    * 关键日志：匹配 Invalid num_sge
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_sg 在执行复制前发现调用方传入的 SGE 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.116 deepcopy_sg 分配 SGE 临时参数失败导致复制流程无法继续
* 故障编号：urma_291
* 故障现象：
    * 关键日志：匹配 Failed to alloc dst sge
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_sg 需要为 SGE 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.117 deepcopy_cas_wr 分配 WR 临时参数失败导致复制流程无法继续
* 故障编号：urma_292
* 故障现象：
    * 关键日志：匹配 Failed to alloc new_wr_cas->dst
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_cas_wr 需要为 WR 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.118 deepcopy_cas_wr 执行复制 WR 失败导致当前资源状态无法推进
* 故障编号：urma_293
* 故障现象：
    * 关键日志：匹配 Failed to deepcopy dst sge
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_cas_wr 调用下层 provider、bond 组件或系统接口处理 WR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.119 deepcopy_cas_wr 分配 WR 临时参数失败导致复制流程无法继续
* 故障编号：urma_294
* 故障现象：
    * 关键日志：匹配 Failed to alloc new_wr_cas->src
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_cas_wr 需要为 WR 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.120 deepcopy_cas_wr 执行复制 WR 失败导致当前资源状态无法推进
* 故障编号：urma_295
* 故障现象：
    * 关键日志：匹配 Failed to copy src sge
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_cas_wr 调用下层 provider、bond 组件或系统接口处理 WR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.121 deepcopy_faa_wr 分配 WR 临时参数失败导致复制流程无法继续
* 故障编号：urma_296
* 故障现象：
    * 关键日志：匹配 Failed to alloc new_wr_faa->dst
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_faa_wr 需要为 WR 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.122 deepcopy_faa_wr 执行复制 WR 失败导致当前资源状态无法推进
* 故障编号：urma_297
* 故障现象：
    * 关键日志：匹配 Failed to deepcopy dst sge
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_faa_wr 调用下层 provider、bond 组件或系统接口处理 WR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.123 deepcopy_faa_wr 分配 WR 临时参数失败导致复制流程无法继续
* 故障编号：urma_298
* 故障现象：
    * 关键日志：匹配 Failed to alloc new_wr_faa->src
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_faa_wr 需要为 WR 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.124 deepcopy_faa_wr 执行复制 WR 失败导致当前资源状态无法推进
* 故障编号：urma_299
* 故障现象：
    * 关键日志：匹配 Failed to deepcopy src sge
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_faa_wr 调用下层 provider、bond 组件或系统接口处理 WR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.125 deepcopy_jfs_wr_node 分配 JFS 临时参数失败导致复制流程无法继续
* 故障编号：urma_300
* 故障现象：
    * 关键日志：匹配 Malloc wr failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_jfs_wr_node 需要为 JFS 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.126 deepcopy_jfs_wr_node 执行复制 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_301
* 故障现象：
    * 关键日志：匹配 Deepcopy sg failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_jfs_wr_node 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.127 deepcopy_jfr_wr_node 分配 JFR 临时参数失败导致复制流程无法继续
* 故障编号：urma_302
* 故障现象：
    * 关键日志：匹配 Malloc wr failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_jfr_wr_node 需要为 JFR 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.128 deepcopy_jfr_wr_node 执行复制 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_303
* 故障现象：
    * 关键日志：匹配 Deepcopy sg failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_jfr_wr_node 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.129 urma_cmd_create_context 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_304
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_context 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.130 urma_cmd_create_context URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_305
* 故障现象：
    * 关键日志：匹配 Failed to query eid
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_context 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 context 状态。
* 解决办法：无
#### 3.131 urma_cmd_create_context URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_306
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_context 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 context 状态。
* 解决办法：无
#### 3.132 urma_cmd_alloc_token_id 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_307
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_alloc_token_id 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.133 urma_cmd_alloc_token_id 分配 token_id 临时参数失败导致分配流程无法继续
* 故障编号：urma_308
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_alloc_token_id, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_alloc_token_id 需要为 token_id 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.134 urma_cmd_alloc_token_id_ex 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_309
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_alloc_token_id_ex 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.135 urma_cmd_alloc_token_id_ex 分配 token_id 临时参数失败导致分配流程无法继续
* 故障编号：urma_310
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_alloc_token_id, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_alloc_token_id_ex 需要为 token_id 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.136 urma_cmd_create_jfs URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_311
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_jfs 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFS 状态。
* 解决办法：无
#### 3.137 urma_cmd_delete_jfs_batch 校验 设备 无效导致删除流程拒绝继续执行
* 故障编号：urma_312
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfs_batch 在执行删除前发现调用方传入的 设备 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.138 urma_cmd_delete_jfs_batch 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_313
* 故障现象：
    * 关键日志：匹配 `jfs not from the same dev, cannot delete in a batch, index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfs_batch 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.139 urma_cmd_delete_jfs_batch 分配 JFS 临时参数失败导致删除流程无法继续
* 故障编号：urma_314
* 故障现象：
    * 关键日志：匹配 Failed to malloc buffer
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfs_batch 需要为 JFS 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.140 urma_cmd_create_jfr 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_315
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_jfr 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.141 urma_cmd_create_jfr URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_316
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_create_jfr, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_jfr 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFR 状态。
* 解决办法：无
#### 3.142 urma_cmd_alloc_jfs 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_317
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_alloc_jfs 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.143 urma_cmd_alloc_jfs 分配 JFS 临时参数失败导致分配流程无法继续
* 故障编号：urma_318
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_alloc_jfr, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_alloc_jfs 需要为 JFS 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.144 urma_cmd_free_jfs 校验 context 无效导致释放流程拒绝继续执行
* 故障编号：urma_319
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_free_jfs 在执行释放前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.145 urma_cmd_set_jfs_opt 校验 JFS 无效导致设置流程拒绝继续执行
* 故障编号：urma_320
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jfs_opt 在执行设置前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.146 urma_cmd_set_jfs_opt 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_321
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jfs_opt 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.147 urma_cmd_delete_jfr_batch 校验 设备 无效导致删除流程拒绝继续执行
* 故障编号：urma_322
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfr_batch 在执行删除前发现调用方传入的 设备 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.148 urma_cmd_delete_jfr_batch 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_323
* 故障现象：
    * 关键日志：匹配 `jfr not from the same dev, cannot delete in a batch, index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfr_batch 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.149 urma_cmd_delete_jfr_batch 分配 JFR 临时参数失败导致删除流程无法继续
* 故障编号：urma_324
* 故障现象：
    * 关键日志：匹配 Failed to malloc buffer
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfr_batch 需要为 JFR 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.150 urma_cmd_create_jfc 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_325
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_jfc 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.151 urma_cmd_create_jfc URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_326
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_create_jfc, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_jfc 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。
* 解决办法：无
#### 3.152 urma_cmd_delete_jfc_batch 校验 设备 无效导致删除流程拒绝继续执行
* 故障编号：urma_327
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfc_batch 在执行删除前发现调用方传入的 设备 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.153 urma_cmd_delete_jfc_batch 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_328
* 故障现象：
    * 关键日志：匹配 `jfc not from the same dev, cannot delete in a batch, index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfc_batch 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.154 urma_cmd_delete_jfc_batch 分配 JFC 临时参数失败导致删除流程无法继续
* 故障编号：urma_329
* 故障现象：
    * 关键日志：匹配 Failed to malloc buffer
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfc_batch 需要为 JFC 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.155 urma_cmd_alloc_jfc 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_330
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_alloc_jfc 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.156 urma_cmd_alloc_jfc 分配 JFC 临时参数失败导致分配流程无法继续
* 故障编号：urma_331
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_alloc_jfc, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_alloc_jfc 需要为 JFC 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.157 urma_cmd_free_jfc 校验 context 无效导致释放流程拒绝继续执行
* 故障编号：urma_332
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_free_jfc 在执行释放前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.158 urma_cmd_set_jfc_opt 校验 JFC 无效导致设置流程拒绝继续执行
* 故障编号：urma_333
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jfc_opt 在执行设置前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.159 urma_cmd_set_jfc_opt 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_334
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jfc_opt 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.160 urma_cmd_set_jfc_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_335
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_set_jfc_opt, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jfc_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。
* 解决办法：无
#### 3.161 urma_cmd_create_jfce 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_336
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_jfce 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.162 urma_cmd_advise_jetty 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_337
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_advise_jetty 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.163 urma_cmd_alloc_jfr 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_338
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_alloc_jfr 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.164 urma_cmd_alloc_jfr 分配 JFR 临时参数失败导致分配流程无法继续
* 故障编号：urma_339
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_alloc_jfr, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_alloc_jfr 需要为 JFR 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.165 urma_cmd_free_jfr 校验 context 无效导致释放流程拒绝继续执行
* 故障编号：urma_340
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_free_jfr 在执行释放前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.166 urma_cmd_set_jfr_opt 校验 JFR 无效导致设置流程拒绝继续执行
* 故障编号：urma_341
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jfr_opt 在执行设置前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.167 urma_cmd_set_jfr_opt 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_342
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jfr_opt 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.168 init_create_jetty_cmd 校验 Jetty 无效导致创建流程拒绝继续执行
* 故障编号：urma_343
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：init_create_jetty_cmd 在执行创建前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.169 init_create_jetty_cmd 校验 Jetty 无效导致创建流程拒绝继续执行
* 故障编号：urma_344
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：init_create_jetty_cmd 在执行创建前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.170 urma_cmd_create_jetty 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_345
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_jetty 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.171 urma_cmd_create_jetty URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_346
* 故障现象：
    * 关键日志：匹配 failed to init create jetty cmd
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_jetty 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 Jetty 状态。
* 解决办法：无
#### 3.172 urma_cmd_create_jetty URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_347
* 故障现象：
    * 关键日志：匹配 failed to fill jetty cfg
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_jetty 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 Jetty 状态。
* 解决办法：无
#### 3.173 urma_cmd_delete_jetty_batch 校验 设备 无效导致删除流程拒绝继续执行
* 故障编号：urma_348
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jetty_batch 在执行删除前发现调用方传入的 设备 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.174 urma_cmd_delete_jetty_batch 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_349
* 故障现象：
    * 关键日志：匹配 `jetty not from the same dev, cannot delete in a batch, index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jetty_batch 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 3.175 urma_cmd_delete_jetty_batch 分配 Jetty 临时参数失败导致删除流程无法继续
* 故障编号：urma_350
* 故障现象：
    * 关键日志：匹配 Failed to malloc buffer
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jetty_batch 需要为 Jetty 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.176 urma_cmd_create_jetty_grp 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_351
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_jetty_grp 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.177 urma_cmd_alloc_jetty 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_352
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_alloc_jetty 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.178 urma_cmd_alloc_jetty 分配 Jetty 临时参数失败导致分配流程无法继续
* 故障编号：urma_353
* 故障现象：
    * 关键日志：匹配 failed to init alloc jetty cmd
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_alloc_jetty 需要为 Jetty 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.179 urma_cmd_alloc_jetty URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_354
* 故障现象：
    * 关键日志：匹配 failed to fill jetty cfg
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_alloc_jetty 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 Jetty 状态。
* 解决办法：无
#### 3.180 urma_cmd_free_jetty 校验 context 无效导致释放流程拒绝继续执行
* 故障编号：urma_355
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_free_jetty 在执行释放前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.181 urma_cmd_set_jetty_opt 校验 Jetty 无效导致设置流程拒绝继续执行
* 故障编号：urma_356
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jetty_opt 在执行设置前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.182 urma_cmd_set_jetty_opt 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_357
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_set_jetty_opt 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.183 urma_cmd_get_net_addr_list 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_358
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_net_addr_list 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.184 urma_cmd_create_notifier 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_359
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_notifier 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.185 urma_cmd_create_notifier URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_360
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_create_notifier, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_create_notifier 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 URMA 对象 状态。
* 解决办法：无
#### 3.186 urma_create_jfc 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_361
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfc 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.187 urma_create_jfc 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_362
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfc 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.188 urma_create_jfc 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_363
* 故障现象：
    * 关键日志：依次匹配 `jfc cfg depth of range, depth:`、`, max_depth:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfc 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 3.189 urma_create_jfc 执行创建 设备 失败导致当前资源状态无法推进
* 故障编号：urma_364
* 故障现象：
    * 关键日志：依次匹配 `[DRV_ERR]Failed to create jfc, dev_name:`、`, eid_idx:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfc 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.190 urma_delete_jfc_batch 校验 JFC 无效导致删除流程拒绝继续执行
* 故障编号：urma_365
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfc_batch 在执行删除前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.191 urma_delete_jfc_batch 分配 context 临时参数失败导致删除流程无法继续
* 故障编号：urma_366
* 故障现象：
    * 关键日志：匹配 Failed to alloc memory
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfc_batch 需要为 context 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.192 urma_delete_jfc_batch 分配 JFCE 临时参数失败导致删除流程无法继续
* 故障编号：urma_367
* 故障现象：
    * 关键日志：匹配 Failed to alloc memory
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfc_batch 需要为 JFCE 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.193 urma_delete_jfc_batch 校验 JFC 无效导致删除流程拒绝继续执行
* 故障编号：urma_368
* 故障现象：
    * 关键日志：匹配 Invalid parameter, jfc in the array is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfc_batch 在执行删除前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.194 urma_alloc_jfc 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_369
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jfc 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.195 urma_alloc_jfc 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_370
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jfc 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.196 urma_alloc_jfc 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_371
* 故障现象：
    * 关键日志：依次匹配 `jfc cfg depth of range, depth:`、`, max_depth:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jfc 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 3.197 urma_alloc_jfc 分配 JFC 临时参数失败导致分配流程无法继续
* 故障编号：urma_372
* 故障现象：
    * 关键日志：匹配 failed to exec ops->alloc_jfc
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jfc 需要为 JFC 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.198 urma_set_jfc_opt 校验 JFC 无效导致设置流程拒绝继续执行
* 故障编号：urma_373
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfc_opt 在执行设置前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.199 urma_set_jfc_opt 校验 JFC 无效导致设置流程拒绝继续执行
* 故障编号：urma_374
* 故障现象：
    * 关键日志：匹配 invalid opt id or opt len
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfc_opt 在执行设置前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.200 urma_set_jfc_opt 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_375
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfc_opt 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.201 urma_set_jfc_opt 执行设置 JFC 失败导致当前资源状态无法推进
* 故障编号：urma_376
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->set_jfc_opt
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfc_opt 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.202 urma_set_jfc_opt 执行设置 JFC 失败导致当前资源状态无法推进
* 故障编号：urma_377
* 故障现象：
    * 关键日志：匹配 Failed to exec urma_jfc_set_options
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfc_opt 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.203 urma_create_jfs 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_378
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfs 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.204 urma_create_jfs 校验 JFS 无效导致创建流程拒绝继续执行
* 故障编号：urma_379
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, trans_mode:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfs 在执行创建前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.205 urma_create_jfs 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_380
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfs 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.206 urma_create_jfs 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_381
* 故障现象：
    * 关键日志：依次匹配 `jfs cfg out of range, depth:`、`, max_depth:`、`, inline_data:`、`, max_inline_len:`、`, sge:`、`, max_sge:`、`, rsge:`、`, max_rsge:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfs 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 3.207 urma_create_jfs 执行创建 设备 失败导致当前资源状态无法推进
* 故障编号：urma_382
* 故障现象：
    * 关键日志：依次匹配 `[DRV_ERR]Failed to create jfs, dev_name:`、`, eid_idx:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfs 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.208 urma_delete_jfs_batch 校验 JFS 无效导致删除流程拒绝继续执行
* 故障编号：urma_383
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfs_batch 在执行删除前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.209 urma_delete_jfs_batch 分配 context 临时参数失败导致删除流程无法继续
* 故障编号：urma_384
* 故障现象：
    * 关键日志：匹配 Failed to alloc memory
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfs_batch 需要为 context 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.210 urma_delete_jfs_batch 校验 JFS 无效导致删除流程拒绝继续执行
* 故障编号：urma_385
* 故障现象：
    * 关键日志：依次匹配 `Invalid parameter, index:`、`jfs in the array is NULL`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfs_batch 在执行删除前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.211 urma_flush_jfs 校验 JFS 无效导致处理流程拒绝继续执行
* 故障编号：urma_386
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_flush_jfs 在执行处理前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.212 urma_flush_jfs 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_387
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_flush_jfs 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.213 urma_alloc_jfs 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_388
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jfs 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.214 urma_alloc_jfs 校验 JFS 无效导致分配流程拒绝继续执行
* 故障编号：urma_389
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, trans_mode:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jfs 在执行分配前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.215 urma_alloc_jfs 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_390
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jfs 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.216 urma_alloc_jfs 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_391
* 故障现象：
    * 关键日志：依次匹配 `jfs cfg out of range, depth:`、`, max_depth:`、`, inline_data:`、`, max_inline_len:`、`, sge:`、`, max_sge:`、`, rsge:`、`, max_rsge:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jfs 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 3.217 urma_set_jfs_opt 校验 JFS 无效导致设置流程拒绝继续执行
* 故障编号：urma_392
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfs_opt 在执行设置前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.218 urma_set_jfs_opt 校验 JFS 无效导致设置流程拒绝继续执行
* 故障编号：urma_393
* 故障现象：
    * 关键日志：匹配 invalid opt id or opt len
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfs_opt 在执行设置前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.219 urma_set_jfs_opt 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_394
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfs_opt 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.220 urma_set_jfs_opt 执行设置 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_395
* 故障现象：
    * 关键日志：匹配 Failed to exec urma_jfr_set_options
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfs_opt 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.221 urma_set_jfs_opt 执行设置 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_396
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->set_jfs_opt
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfs_opt 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.222 urma_create_jfr 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_397
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfr 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.223 urma_create_jfr 校验 JFR 无效导致创建流程拒绝继续执行
* 故障编号：urma_398
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, trans_mode:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfr 在执行创建前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.224 urma_create_jfr 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_399
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfr 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.225 urma_create_jfr 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_400
* 故障现象：
    * 关键日志：依次匹配 `jfr cfg out of range, depth:`、`, max_depth:`、`, sge:`、`, max_sge:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfr 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 3.226 urma_create_jfr 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_401
* 故障现象：
    * 关键日志：依次匹配 `[DRV_ERR]Failed to create jfr, dev_name:`、`, eid_idex:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfr 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 3.227 urma_delete_jfr_batch 校验 JFR 无效导致删除流程拒绝继续执行
* 故障编号：urma_402
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfr_batch 在执行删除前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.228 urma_delete_jfr_batch 分配 context 临时参数失败导致删除流程无法继续
* 故障编号：urma_403
* 故障现象：
    * 关键日志：匹配 Failed to alloc memory
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfr_batch 需要为 context 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.229 urma_delete_jfr_batch 校验 JFR 无效导致删除流程拒绝继续执行
* 故障编号：urma_404
* 故障现象：
    * 关键日志：依次匹配 `Invalid parameter, index:`、`jfr in the array is NULL`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfr_batch 在执行删除前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.230 urma_unimport_jfr 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_405
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unimport_jfr 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.231 urma_alloc_jfr 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_406
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jfr 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.232 urma_alloc_jfr 校验 JFR 无效导致分配流程拒绝继续执行
* 故障编号：urma_407
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, trans_mode:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jfr 在执行分配前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.233 urma_alloc_jfr 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_408
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jfr 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.234 urma_alloc_jfr 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_409
* 故障现象：
    * 关键日志：依次匹配 `jfr cfg out of range, depth:`、`, max_depth:`、`, sge:`、`, max_sge:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jfr 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 3.235 urma_set_jfr_opt 校验 JFR 无效导致设置流程拒绝继续执行
* 故障编号：urma_410
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfr_opt 在执行设置前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.236 urma_set_jfr_opt 校验 JFR 无效导致设置流程拒绝继续执行
* 故障编号：urma_411
* 故障现象：
    * 关键日志：匹配 invalid opt id or opt len
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfr_opt 在执行设置前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.237 urma_set_jfr_opt 执行设置 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_412
* 故障现象：
    * 关键日志：匹配 Failed to exec urma_jfr_set_options
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfr_opt 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.238 urma_set_jfr_opt 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_413
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfr_opt 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.239 urma_set_jfr_opt 执行设置 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_414
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->set_jfr_opt
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jfr_opt 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.240 urma_create_jfce 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_415
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfce 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：当前预期不会出现，如果 fd 超规格可能导致失败，此时需要修改系统 fd 规格数，或者减小应用创建 jfce 的数量
#### 3.241 urma_create_jfce 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_416
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfce 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：当前预期不会出现，如果 fd 超规格可能导致失败，此时需要修改系统 fd 规格数，或者减小应用创建 jfce 的数量
#### 3.242 urma_create_jfce 执行创建 设备 失败导致当前资源状态无法推进
* 故障编号：urma_417
* 故障现象：
    * 关键日志：依次匹配 `[DRV_ERR]Failed to create jfce, dev_name:`、`, eid_idx:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jfce 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：当前预期不会出现，如果 fd 超规格可能导致失败，此时需要修改系统 fd 规格数，或者减小应用创建 jfce 的数量
#### 3.243 urma_create_jetty_check_trans_mode 校验 Jetty 无效导致创建流程拒绝继续执行
* 故障编号：urma_418
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, trans_mode:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_check_trans_mode 在执行创建前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.244 urma_create_jetty_check_trans_mode 执行创建 context 失败导致当前资源状态无法推进
* 故障编号：urma_419
* 故障现象：
    * 关键日志：匹配 UB dev should use share jfr!
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_check_trans_mode 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.245 urma_create_jetty_check_trans_mode 校验 Jetty 无效导致创建流程拒绝继续执行
* 故障编号：urma_420
* 故障现象：
    * 关键日志：依次匹配 `Invalid parameter, trans_mode:`、`, order_type:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_check_trans_mode 在执行创建前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.246 urma_create_jetty_check_trans_mode 校验 Jetty 无效导致创建流程拒绝继续执行
* 故障编号：urma_421
* 故障现象：
    * 关键日志：匹配 jfr cfg is null or trans_mode or order_type invalid with non shared jfr flag
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_check_trans_mode 在执行创建前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.247 urma_create_jetty_check_trans_mode 校验 Jetty 无效导致创建流程拒绝继续执行
* 故障编号：urma_422
* 故障现象：
    * 关键日志：匹配 jfr is null or trans_mode or order_type invalid with shared jfr flag
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_check_trans_mode 在执行创建前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.248 urma_create_jetty_check_dev_cap 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_423
* 故障现象：
    * 关键日志：依次匹配 `jetty_grp jetty cnt:`、`, max_jetty in grp:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_check_dev_cap 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 3.249 urma_create_jetty_check_dev_cap 执行创建 设备 失败导致当前资源状态无法推进
* 故障编号：urma_424
* 故障现象：
    * 关键日志：依次匹配 `jetty cfg out of range, jfs_depth:`、`, max_jfs_depth:`、`, inline_data:`、`, max_jfs_inline_len:`、`, jfr_depth:`、`, max_jfr_depth:`、`, jfs_sge:`、`, max_jfs_sge:`、`, jfs_rsge:`、`, max_jfs_rsge:`、`, jfr_sge:`、`, max_jfr_sge:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_check_dev_cap 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.250 urma_create_jetty_check_jfc 校验 Jetty 无效导致创建流程拒绝继续执行
* 故障编号：urma_425
* 故障现象：
    * 关键日志：匹配 Invalid parameter, jfc is NULL in jfs_cfg
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_check_jfc 在执行创建前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.251 urma_create_jetty_check_jfc 校验 Jetty 无效导致创建流程拒绝继续执行
* 故障编号：urma_426
* 故障现象：
    * 关键日志：匹配 Invalid parameter, jfr cfg is null or jfc is NULL with non shared jfr flag
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_check_jfc 在执行创建前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.252 urma_create_jetty_check_jfc 校验 Jetty 无效导致创建流程拒绝继续执行
* 故障编号：urma_427
* 故障现象：
    * 关键日志：匹配 Invalid parameter, jfr is null or jfc is NULL with shared jfr flag
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_check_jfc 在执行创建前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.253 urma_create_jetty 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_428
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.254 urma_create_jetty 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_429
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.255 urma_create_jetty 执行创建 设备 失败导致当前资源状态无法推进
* 故障编号：urma_430
* 故障现象：
    * 关键日志：依次匹配 `[DRV_ERR]create_jetty failed, dev_name:`、`, eid_idx:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.256 urma_delete_jetty_batch 校验 Jetty 无效导致删除流程拒绝继续执行
* 故障编号：urma_431
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty_batch 在执行删除前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.257 urma_delete_jetty_batch 分配 context 临时参数失败导致删除流程无法继续
* 故障编号：urma_432
* 故障现象：
    * 关键日志：匹配 Failed to alloc memory
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty_batch 需要为 context 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.258 urma_delete_jetty_batch 校验 Jetty 无效导致删除流程拒绝继续执行
* 故障编号：urma_433
* 故障现象：
    * 关键日志：依次匹配 `Invalid parameter, index`、`jetty in the array is NULL`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty_batch 在执行删除前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.259 urma_import_jetty_async 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_434
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jetty_async 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.260 urma_import_jetty_async 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_435
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jetty_async 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.261 urma_import_jetty_async 分配 目标 Jetty 临时参数失败导致导入流程无法继续
* 故障编号：urma_436
* 故障现象：
    * 关键日志：匹配 Failed to alloc incomplete_tjetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jetty_async 需要为 目标 Jetty 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.262 urma_alloc_jetty 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_437
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jetty 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.263 urma_alloc_jetty 校验 Jetty 无效导致分配流程拒绝继续执行
* 故障编号：urma_438
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jetty 在执行分配前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.264 urma_alloc_jetty 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_439
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jetty 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.265 urma_alloc_jetty 校验 Jetty 无效导致分配流程拒绝继续执行
* 故障编号：urma_440
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jetty 在执行分配前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.266 urma_alloc_jetty 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_441
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jetty 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.267 urma_alloc_jetty 分配 Jetty 临时参数失败导致分配流程无法继续
* 故障编号：urma_442
* 故障现象：
    * 关键日志：匹配 alloc_jetty failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_jetty 需要为 Jetty 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.268 urma_set_jetty_opt 校验 Jetty 无效导致设置流程拒绝继续执行
* 故障编号：urma_443
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jetty_opt 在执行设置前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.269 urma_set_jetty_opt 校验 Jetty 无效导致设置流程拒绝继续执行
* 故障编号：urma_444
* 故障现象：
    * 关键日志：匹配 invalid opt id or opt len
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jetty_opt 在执行设置前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.270 urma_set_jetty_opt 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_445
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jetty_opt 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.271 urma_set_jetty_opt 执行设置 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_446
* 故障现象：
    * 关键日志：匹配 Failed to exec urma_delete_jetty_to_jetty_grp
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jetty_opt 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.272 urma_set_jetty_opt 执行设置 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_447
* 故障现象：
    * 关键日志：匹配 Failed to exec urma_jetty_set_options
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jetty_opt 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.273 urma_set_jetty_opt 执行设置 context 失败导致当前资源状态无法推进
* 故障编号：urma_448
* 故障现象：
    * 关键日志：匹配 UB dev should use share jfr!
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jetty_opt 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.274 urma_set_jetty_opt 执行设置 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_449
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->set_jetty_opt
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jetty_opt 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.275 urma_set_jetty_opt 执行设置 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_450
* 故障现象：
    * 关键日志：匹配 Failed to exec urma_add_jetty_to_jetty_grp
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_jetty_opt 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.276 urma_create_notifier 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_451
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_notifier 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.277 urma_create_notifier 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_452
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_notifier 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.278 urma_create_notifier 分配 URMA 对象 临时参数失败导致创建流程无法继续
* 故障编号：urma_453
* 故障现象：
    * 关键日志：匹配 Failed to alloc notifier
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_notifier 需要为 URMA 对象 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.279 urma_create_jetty_grp 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_454
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_grp 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.280 urma_create_jetty_grp 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_455
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_grp 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.281 urma_create_jetty_grp 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_456
* 故障现象：
    * 关键日志：匹配 max_jetty_in_jetty_grp is err
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_grp 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 3.282 urma_create_jetty_grp 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_457
* 故障现象：
    * 关键日志：匹配 create_jetty_grp failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_grp 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 3.283 urma_create_jetty_grp 分配 Jetty 临时参数失败导致创建流程无法继续
* 故障编号：urma_458
* 故障现象：
    * 关键日志：匹配 alloc jetty list failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_grp 需要为 Jetty 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。
* 解决办法：无
#### 3.284 urma_create_jetty_grp 执行创建 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_459
* 故障现象：
    * 关键日志：匹配 delete_jetty_grp failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_jetty_grp 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.285 urma_unimport_seg 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_460
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unimport_seg 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.286 urma_alloc_token_id 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_461
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_token_id 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.287 urma_alloc_token_id 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_462
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_token_id 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.288 urma_alloc_token_id 执行分配 设备 失败导致当前资源状态无法推进
* 故障编号：urma_463
* 故障现象：
    * 关键日志：依次匹配 `[DRV_ERR]Failed to register seg, dev_name:`、`, eid_idx:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_token_id 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.289 urma_alloc_token_id_ex 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_464
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_token_id_ex 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.290 urma_alloc_token_id_ex 校验 context 无效导致分配流程拒绝继续执行
* 故障编号：urma_465
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_token_id_ex 在执行分配前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.291 urma_alloc_token_id_ex 校验 设备 业务条件不满足导致分配流程拒绝继续执行
* 故障编号：urma_466
* 故障现象：
    * 关键日志：匹配 dev not support token id table mode
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_token_id_ex 在执行分配时发现 设备 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 3.292 urma_free_token_id 校验 token_id 无效导致释放流程拒绝继续执行
* 故障编号：urma_467
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_token_id 在执行释放前发现调用方传入的 token_id 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.293 urma_register_seg 校验 context 无效导致注册流程拒绝继续执行
* 故障编号：urma_468
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_register_seg 在执行注册前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.294 urma_register_seg 校验 context 无效导致注册流程拒绝继续执行
* 故障编号：urma_469
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_register_seg 在执行注册前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.295 urma_register_seg 校验 context 无效导致注册流程拒绝继续执行
* 故障编号：urma_470
* 故障现象：
    * 关键日志：依次匹配 `[DRV_ERR]register seg failed, dev_name:`、`, eid_idx:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_register_seg 在执行注册前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.296 urma_user_ctl 执行处理 URMA 对象 失败导致当前资源状态无法推进
* 故障编号：urma_471
* 故障现象：
    * 关键日志：匹配 `Failed to excecute user_ctl, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_user_ctl 调用下层 provider、bond 组件或系统接口处理 URMA 对象 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.297 urma_get_net_addr_list 校验 URMA 对象 无效导致获取流程拒绝继续执行
* 故障编号：urma_472
* 故障现象：
    * 关键日志：匹配 Invalid parameter with max_netaddr_cnt as 0
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_net_addr_list 在执行获取前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.298 urma_get_net_addr_list 执行获取 URMA 对象 失败导致当前资源状态无法推进
* 故障编号：urma_473
* 故障现象：
    * 关键日志：依次匹配 `Failed to get netaddr list, ret:`、`, max_netaddr_cnt:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_net_addr_list 调用下层 provider、bond 组件或系统接口处理 URMA 对象 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.299 urma_read_sysfs_device 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_474
* 故障现象：
    * 关键日志：匹配 snprintf failed, dev_name
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_read_sysfs_device 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 3.300 urma_alloc_device 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_475
* 故障现象：
    * 关键日志：匹配 snprintf failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_alloc_device 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 3.301 urma_discover_devices 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_476
* 故障现象：
    * 关键日志：依次匹配 `Failed close dir:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_discover_devices 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 3.302 urma_log_set_thread_tag 校验 URMA 对象 无效导致读取流程拒绝继续执行
* 故障编号：urma_477
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_log_set_thread_tag 在执行读取前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.303 urma_open_provider 打开 provider 失败导致打开无法访问底层资源
* 故障编号：urma_478
* 故障现象：
    * 关键日志：匹配 doesn't exist or doesn't have permission
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_open_provider 需要访问 provider 对应的文件、目录、provider 动态库或字符设备，但路径不存在、权限不足或系统调用失败，导致后续 URMA 设备枚举、provider 装载或上下文创建无法进行。
* 解决办法：无
#### 3.304 urma_open_provider 打开 provider 失败导致打开无法访问底层资源
* 故障编号：urma_479
* 故障现象：
    * 关键日志：匹配 realpath failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_open_provider 需要访问 provider 对应的文件、目录、provider 动态库或字符设备，但路径不存在、权限不足或系统调用失败，导致后续 URMA 设备枚举、provider 装载或上下文创建无法进行。
* 解决办法：无
#### 3.305 urma_open_provider 打开 provider 失败导致打开无法访问底层资源
* 故障编号：urma_480
* 故障现象：
    * 关键日志：匹配 open failed, err
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_open_provider 需要访问 provider 对应的文件、目录、provider 动态库或字符设备，但路径不存在、权限不足或系统调用失败，导致后续 URMA 设备枚举、provider 装载或上下文创建无法进行。
* 解决办法：无
#### 3.306 urma_get_eid_list 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_481
* 故障现象：
    * 关键日志：匹配 max eid cnt is err
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_eid_list 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：执行 `lsmod | grep udma` 检查驱动是否加载，执行 `urma_admin show -a` 查看 UB 设备是否存在，部署完成后重试
#### 3.307 urma_create_context 校验 context 无效导致创建流程拒绝继续执行
* 故障编号：urma_482
* 故障现象：
    * 关键日志：匹配 Invalid parameter with err dev or ops
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_context 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：当前不会触发
#### 3.308 urma_create_context 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_483
* 故障现象：
    * 关键日志：匹配 Failed to query eid
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_context 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：当前不会触发
#### 3.309 urma_create_context 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_484
* 故障现象：
    * 关键日志：匹配 Failed to open urma cdev with path , dev_fd
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_context 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：当前不会触发
#### 3.310 urma_create_context 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_485
* 故障现象：
    * 关键日志：匹配 [DRV_ERR]Failed to create urma context
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_create_context 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：当前不会触发
#### 3.311 urma_set_context_opt 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_486
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_context_opt 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.312 urma_set_context_opt 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_487
* 故障现象：
    * 关键日志：匹配 Invalid option value len
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_context_opt 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.313 urma_set_context_opt 执行设置 context 失败导致当前资源状态无法推进
* 故障编号：urma_488
* 故障现象：
    * 关键日志：匹配 Cannot set aggregated mode for non-aggregated device
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_context_opt 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 3.314 urma_set_context_opt 校验 context 无效导致设置流程拒绝继续执行
* 故障编号：urma_489
* 故障现象：
    * 关键日志：匹配 Invalid option name
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_set_context_opt 在执行设置前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 3.315 urma_get_uasid 校验 URMA 对象 无效导致获取流程拒绝继续执行
* 故障编号：urma_490
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_uasid 在执行获取前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
### 4 资源查询失败
* 故障编号：urma_491
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 4.1 bondp_query_jfr 执行查询 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_492
* 故障现象：
    * 关键日志：依次匹配 `query pjfr fail, index:`、`, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_query_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 4.2 bondp_jfs_get_args_list 校验 JFS 无效导致获取流程拒绝继续执行
* 故障编号：urma_493
* 故障现象：
    * 关键日志：匹配 Invalid param jfc
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_jfs_get_args_list 在执行获取前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.3 bondp_jetty_get_args_list 校验 Jetty 无效导致获取流程拒绝继续执行
* 故障编号：urma_494
* 故障现象：
    * 关键日志：匹配 Invalid param jetty cfg
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_jetty_get_args_list 在执行获取前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.4 get_comp_urma_jetty_id 校验 Jetty 无效导致获取流程拒绝继续执行
* 故障编号：urma_495
* 故障现象：
    * 关键日志：匹配 Failed to get_comp_urma_jetty, Invalid type
    * 日志路径：URMA_LOG_PATH
* 故障原因：get_comp_urma_jetty_id 在执行获取前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.5 get_bjetty_ctx_by_cr 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_496
* 故障现象：
    * 关键日志：匹配 `Failed to get comp, local_id:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：get_bjetty_ctx_by_cr 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 4.6 get_bjetty_ctx_by_cr 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_497
* 故障现象：
    * 关键日志：匹配 Null bjetty_ctx in bdp_comp
    * 日志路径：URMA_LOG_PATH
* 故障原因：get_bjetty_ctx_by_cr 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 4.7 get_dev_and_ctx_by_name 执行获取 context 失败导致当前资源状态无法推进
* 故障编号：urma_498
* 故障现象：
    * 关键日志：匹配 Failed to get device
    * 日志路径：URMA_LOG_PATH
* 故障原因：get_dev_and_ctx_by_name 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 4.8 get_dev_and_ctx_by_name 执行获取 context 失败导致当前资源状态无法推进
* 故障编号：urma_499
* 故障现象：
    * 关键日志：匹配 Failed to get eid_idx
    * 日志路径：URMA_LOG_PATH
* 故障原因：get_dev_and_ctx_by_name 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 4.9 get_dev_and_ctx_by_name 执行获取 context 失败导致当前资源状态无法推进
* 故障编号：urma_500
* 故障现象：
    * 关键日志：匹配 Failed to create context
    * 日志路径：URMA_LOG_PATH
* 故障原因：get_dev_and_ctx_by_name 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 4.10 get_dev_and_ctx_by_eid 执行获取 context 失败导致当前资源状态无法推进
* 故障编号：urma_501
* 故障现象：
    * 关键日志：匹配 Failed to create context
    * 日志路径：URMA_LOG_PATH
* 故障原因：get_dev_and_ctx_by_eid 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 4.11 get_topo_info_from_ko 执行获取 context 失败导致当前资源状态无法推进
* 故障编号：urma_502
* 故障现象：
    * 关键日志：匹配 Failed to get topo info, change to general mode
    * 日志路径：URMA_LOG_PATH
* 故障原因：get_topo_info_from_ko 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 4.12 get_topo_info_from_ko 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_503
* 故障现象：
    * 关键日志：匹配 Failed to create topo map
    * 日志路径：URMA_LOG_PATH
* 故障原因：get_topo_info_from_ko 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 4.13 urma_cmd_query_jfs 校验 context 无效导致查询流程拒绝继续执行
* 故障编号：urma_504
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_query_jfs 在执行查询前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.14 urma_cmd_query_jfs URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_505
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_query_jfs 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFS 状态。
* 解决办法：无
#### 4.15 urma_cmd_query_jfr 校验 context 无效导致查询流程拒绝继续执行
* 故障编号：urma_506
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_query_jfr 在执行查询前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.16 urma_cmd_query_jfr URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_507
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_query_jfr 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFR 状态。
* 解决办法：无
#### 4.17 urma_cmd_query_jetty 校验 context 无效导致查询流程拒绝继续执行
* 故障编号：urma_508
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_query_jetty 在执行查询前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.18 urma_cmd_query_jetty 校验 Jetty 无效导致查询流程拒绝继续执行
* 故障编号：urma_509
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_query_jetty 在执行查询前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.19 urma_cmd_get_ip_by_eid 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_510
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_ip_by_eid 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.20 urma_cmd_get_smac 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_511
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_smac 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.21 urma_cmd_get_dmac 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_512
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_dmac 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.22 urma_get_jfc_opt 校验 JFC 无效导致获取流程拒绝继续执行
* 故障编号：urma_513
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_jfc_opt 在执行获取前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.23 urma_get_jfc_opt 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_514
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_jfc_opt 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.24 urma_get_jfc_opt 执行获取 JFC 失败导致当前资源状态无法推进
* 故障编号：urma_515
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->get_jfc_opt
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_jfc_opt 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 4.25 urma_query_jfs 校验 JFS 无效导致查询流程拒绝继续执行
* 故障编号：urma_516
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_query_jfs 在执行查询前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.26 urma_query_jfs 校验 context 无效导致查询流程拒绝继续执行
* 故障编号：urma_517
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_query_jfs 在执行查询前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.27 urma_get_jfs_opt 校验 JFS 无效导致获取流程拒绝继续执行
* 故障编号：urma_518
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_jfs_opt 在执行获取前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.28 urma_get_jfs_opt 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_519
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_jfs_opt 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.29 urma_get_jfs_opt 执行获取 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_520
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->get_jfs_opt
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_jfs_opt 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 4.30 urma_query_jfr 校验 JFR 无效导致查询流程拒绝继续执行
* 故障编号：urma_521
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_query_jfr 在执行查询前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.31 urma_query_jfr 校验 context 无效导致查询流程拒绝继续执行
* 故障编号：urma_522
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_query_jfr 在执行查询前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.32 urma_get_jfr_opt 校验 JFR 无效导致获取流程拒绝继续执行
* 故障编号：urma_523
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_jfr_opt 在执行获取前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.33 urma_get_jfr_opt 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_524
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_jfr_opt 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.34 urma_get_jfr_opt 执行获取 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_525
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->get_jfr_opt
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_jfr_opt 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 4.35 urma_query_jetty 校验 Jetty 无效导致查询流程拒绝继续执行
* 故障编号：urma_526
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_query_jetty 在执行查询前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.36 urma_query_jetty 校验 context 无效导致查询流程拒绝继续执行
* 故障编号：urma_527
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_query_jetty 在执行查询前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.37 urma_get_jetty_opt 校验 Jetty 无效导致获取流程拒绝继续执行
* 故障编号：urma_528
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_jetty_opt 在执行获取前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.38 urma_get_jetty_opt 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_529
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_jetty_opt 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.39 urma_get_jetty_opt 执行获取 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_530
* 故障现象：
    * 关键日志：匹配 Failed to exec ops->get_jetty_opt
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_jetty_opt 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 4.40 urma_get_ip_by_eid 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_531
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_ip_by_eid 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.41 urma_get_ip_by_eid 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_532
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_ip_by_eid 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.42 urma_get_smac 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_533
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_smac 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.43 urma_get_smac 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_534
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_smac 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.44 urma_get_dmac 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_535
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_dmac 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.45 urma_get_dmac 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_536
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_dmac 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.46 urma_read_sysfs_file 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_537
* 故障现象：
    * 关键日志：匹配 snprintf failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_read_sysfs_file 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 4.47 urma_read_sysfs_file 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_538
* 故障现象：
    * 关键日志：依次匹配 `Failed open file:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_read_sysfs_file 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 4.48 urma_read_sysfs_file 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_539
* 故障现象：
    * 关键日志：依次匹配 `Failed read file:`、`, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_read_sysfs_file 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 4.49 read_eid_list_sysyf 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_540
* 故障现象：
    * 关键日志：匹配 printf failed, eid idx
    * 日志路径：URMA_LOG_PATH
* 故障原因：read_eid_list_sysyf 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 4.50 read_eid_list_sysyf 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_541
* 故障现象：
    * 关键日志：匹配 Failed to read sysfs file
    * 日志路径：URMA_LOG_PATH
* 故障原因：read_eid_list_sysyf 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 4.51 read_eid_sysfs_with_index 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_542
* 故障现象：
    * 关键日志：匹配 snprintf failed, eid idx
    * 日志路径：URMA_LOG_PATH
* 故障原因：read_eid_sysfs_with_index 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 4.52 read_eid_sysfs_with_index URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_543
* 故障现象：
    * 关键日志：匹配 Failed to read sysfs file
    * 日志路径：URMA_LOG_PATH
* 故障原因：read_eid_sysfs_with_index 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 设备 状态。
* 解决办法：无
#### 4.53 read_eid_sysfs_with_index URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_544
* 故障现象：
    * 关键日志：依次匹配 `Failed to parse eid value, dev name:`、`, eid idx:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：read_eid_sysfs_with_index 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 设备 状态。
* 解决办法：无
#### 4.54 urma_ioctl_get_eid_list URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_545
* 故障现象：
    * 关键日志：匹配 Failed to open urma cdev with path
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_ioctl_get_eid_list 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 设备 状态。
* 解决办法：无
#### 4.55 urma_query_device_attr 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_546
* 故障现象：
    * 关键日志：匹配 Failed to get cdev_path, dev_name
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_query_device_attr 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 4.56 urma_query_device_attr 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_547
* 故障现象：
    * 关键日志：匹配 Failed to open urma cdev, path
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_query_device_attr 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 4.57 urma_parse_rsvd_jetty_range 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_548
* 故障现象：
    * 关键日志：匹配 parse sysfs: failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_parse_rsvd_jetty_range 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 4.58 urma_parse_rsvd_jetty_range 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_549
* 故障现象：
    * 关键日志：匹配 parse rsvd jetty: failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_parse_rsvd_jetty_range 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 4.59 urma_parse_port_attr 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_550
* 故障现象：
    * 关键日志：依次匹配 `snprintf failed, path:`、`, port_num:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_parse_port_attr 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 4.60 urma_read 校验 JFS 无效导致读取流程拒绝继续执行
* 故障编号：urma_551
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_read 在执行读取前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.61 urma_getenv_log_level 校验 URMA 对象 无效导致获取流程拒绝继续执行
* 故障编号：urma_552
* 故障现象：
    * 关键日志：匹配 Invalid parameter: log level str
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_getenv_log_level 在执行获取前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.62 urma_get_device_list 校验 设备 无效导致获取流程拒绝继续执行
* 故障编号：urma_553
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_device_list 在执行获取前发现调用方传入的 设备 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：执行 `lsmod | grep udma` 检查驱动是否加载，执行 `urma_admin show -a` 查看 UB 设备是否存在，部署完成后重试
#### 4.63 urma_query_device 校验 设备 无效导致查询流程拒绝继续执行
* 故障编号：urma_554
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_query_device 在执行查询前发现调用方传入的 设备 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 4.64 urma_query_device 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_555
* 故障现象：
    * 关键日志：匹配 `Failed to query device attr, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_query_device 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 4.65 urma_get_device_by_name 校验 设备 无效导致获取流程拒绝继续执行
* 故障编号：urma_556
* 故障现象：
    * 关键日志：匹配 Invalid dev_name
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_device_by_name 在执行获取前发现调用方传入的 设备 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：执行 `lsmod | grep udma` 检查驱动是否加载，执行 `urma_admin show -a` 查看 UB 设备是否存在，部署完成后重试
#### 4.66 urma_get_device_by_name 执行获取 设备 失败导致当前资源状态无法推进
* 故障编号：urma_557
* 故障现象：
    * 关键日志：匹配 urma get device list failed, device_num
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_device_by_name 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：执行 `lsmod | grep udma` 检查驱动是否加载，执行 `urma_admin show -a` 查看 UB 设备是否存在，部署完成后重试
#### 4.67 urma_get_device_by_name 校验 设备 业务条件不满足导致获取流程拒绝继续执行
* 故障编号：urma_558
* 故障现象：
    * 关键日志：匹配 device list name: does not match dev_name
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_device_by_name 在执行获取时发现 设备 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：执行 `lsmod | grep udma` 检查驱动是否加载，执行 `urma_admin show -a` 查看 UB 设备是否存在，部署完成后重试
#### 4.68 urma_get_device_by_eid 执行获取 设备 失败导致当前资源状态无法推进
* 故障编号：urma_559
* 故障现象：
    * 关键日志：匹配 urma get device list failed!
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_device_by_eid 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
### 5 资源导入/注册失败
* 故障编号：urma_560
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 5.1 import_pjetty_for_primary_eid 执行导入 context 失败导致当前资源状态无法推进
* 故障编号：urma_561
* 故障现象：
    * 关键日志：匹配 Primary dev has NULL ctx
    * 日志路径：URMA_LOG_PATH
* 故障原因：import_pjetty_for_primary_eid 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 5.2 import_pjetty_for_primary_eid 执行导入 设备 失败导致当前资源状态无法推进
* 故障编号：urma_562
* 故障现象：
    * 关键日志：匹配 Primary dev has NULL rjetty eid
    * 日志路径：URMA_LOG_PATH
* 故障原因：import_pjetty_for_primary_eid 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 5.3 import_pjetty_for_primary_eid 执行导入 EID 失败导致当前资源状态无法推进
* 故障编号：urma_563
* 故障现象：
    * 关键日志：匹配 Failed to import primary tjetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：import_pjetty_for_primary_eid 调用下层 provider、bond 组件或系统接口处理 EID 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 5.4 import_pjetty_for_port_eid 执行导入 EID 失败导致当前资源状态无法推进
* 故障编号：urma_564
* 故障现象：
    * 关键日志：匹配 Failed to import direct tjetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：import_pjetty_for_port_eid 调用下层 provider、bond 组件或系统接口处理 EID 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 5.5 import_pjetty_for_port_eid 校验 EID 业务条件不满足导致导入流程拒绝继续执行
* 故障编号：urma_565
* 故障现象：
    * 关键日志：匹配 No valid direct route
    * 日志路径：URMA_LOG_PATH
* 故障原因：import_pjetty_for_port_eid 在执行导入时发现 EID 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 5.6 bondp_import_jetty 执行导入 context 失败导致当前资源状态无法推进
* 故障编号：urma_566
* 故障现象：
    * 关键日志：匹配 Failed to add remote jetty id info
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_jetty 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 5.7 bondp_unimport_jetty 校验 目标 Jetty 无效导致导入流程拒绝继续执行
* 故障编号：urma_567
* 故障现象：
    * 关键日志：匹配 Invalid bdp tjetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_unimport_jetty 在执行导入前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.8 bondp_import_pjfr 校验 目标 Jetty 业务条件不满足导致导入流程拒绝继续执行
* 故障编号：urma_568
* 故障现象：
    * 关键日志：匹配 Currently, jfr does not support single-path mode
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_pjfr 在执行导入时发现 目标 Jetty 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 5.9 bondp_unimport_jfr 校验 目标 Jetty 无效导致导入流程拒绝继续执行
* 故障编号：urma_569
* 故障现象：
    * 关键日志：匹配 Invalid bdp tjetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_unimport_jfr 在执行导入前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.10 bondp_v_segment_register 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_570
* 故障现象：
    * 关键日志：匹配 `Fail to register seg, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_v_segment_register 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 5.11 bdp_r_v2p_token_id_del_idx_lockless 执行处理 token_id 失败导致当前资源状态无法推进
* 故障编号：urma_571
* 故障现象：
    * 关键日志：匹配 `Failed to find node, index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_r_v2p_token_id_del_idx_lockless 调用下层 provider、bond 组件或系统接口处理 token_id 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 5.12 bondp_unregister_seg 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_572
* 故障现象：
    * 关键日志：匹配 bondp_hash_table_lookup fail
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_unregister_seg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 5.13 bondp_unregister_seg 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_573
* 故障现象：
    * 关键日志：依次匹配 `Failed to delete vseg, token_id:`、`, handle:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_unregister_seg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 5.14 bondp_unregister_seg 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_574
* 故障现象：
    * 关键日志：依次匹配 `Failed to delete pseg for vseg, token_id:`、`, handle:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_unregister_seg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 5.15 import_pseg 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_575
* 故障现象：
    * 关键日志：匹配 `Failed to import seg (`
    * 日志路径：URMA_LOG_PATH
* 故障原因：import_pseg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 5.16 import_pseg_for_port_eid 校验 EID 业务条件不满足导致导入流程拒绝继续执行
* 故障编号：urma_576
* 故障现象：
    * 关键日志：匹配 No valid direct route
    * 日志路径：URMA_LOG_PATH
* 故障原因：import_pseg_for_port_eid 在执行导入时发现 EID 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 5.17 bondp_import_seg 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_577
* 故障现象：
    * 关键日志：匹配 `Failed to lookup v2p_token_id, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_seg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 5.18 bondp_import_seg 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_578
* 故障现象：
    * 关键日志：匹配 Failed to import vseg
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_seg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 5.19 bondp_import_seg 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_579
* 故障现象：
    * 关键日志：匹配 Failed to import pseg
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_import_seg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 5.20 urma_cmd_free_token_id 校验 context 无效导致释放流程拒绝继续执行
* 故障编号：urma_580
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_free_token_id 在执行释放前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.21 urma_cmd_free_token_id URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_581
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_free_token_id 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 token_id 状态。
* 解决办法：无
#### 5.22 urma_cmd_register_seg 校验 context 无效导致注册流程拒绝继续执行
* 故障编号：urma_582
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_register_seg 在执行注册前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.23 urma_cmd_register_seg URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_583
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_register_seg, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_register_seg 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 segment 状态。
* 解决办法：无
#### 5.24 urma_cmd_unregister_seg 校验 context 无效导致注册流程拒绝继续执行
* 故障编号：urma_584
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_unregister_seg 在执行注册前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.25 urma_cmd_unregister_seg URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_585
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_unregister_seg 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 segment 状态。
* 解决办法：无
#### 5.26 urma_cmd_import_seg 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_586
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_import_seg 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.27 urma_cmd_unimport_seg 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_587
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_unimport_seg 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.28 urma_cmd_unimport_jfr 校验 JFR 无效导致导入流程拒绝继续执行
* 故障编号：urma_588
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_unimport_jfr 在执行导入前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.29 urma_cmd_unimport_jetty 校验 目标 Jetty 无效导致导入流程拒绝继续执行
* 故障编号：urma_589
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_unimport_jetty 在执行导入前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.30 urma_cmd_unimport_jetty_async 校验 目标 Jetty 无效导致导入流程拒绝继续执行
* 故障编号：urma_590
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_unimport_jetty_async 在执行导入前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.31 urma_import_jfr 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_591
* 故障现象：
    * 关键日志：匹配 Token value must be set when token policy is not URMA_TOKEN_NONE
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jfr 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：UDMA 错误定界；建链交换信息失败，可重试
#### 5.32 urma_import_jfr_ex 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_592
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jfr_ex 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.33 urma_import_jfr_ex 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_593
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jfr_ex 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.34 urma_unimport_jfr 校验 JFR 无效导致导入流程拒绝继续执行
* 故障编号：urma_594
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unimport_jfr 在执行导入前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.35 urma_import_jetty 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_595
* 故障现象：
    * 关键日志：匹配 Token value must be set when token policy is not URMA_TOKEN_NONE
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jetty 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 5.36 urma_import_jetty_ex 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_596
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jetty_ex 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.37 urma_import_jetty_ex 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_597
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_jetty_ex 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.38 urma_unimport_jetty 校验 目标 Jetty 无效导致导入流程拒绝继续执行
* 故障编号：urma_598
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unimport_jetty 在执行导入前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.39 urma_unimport_jetty 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_599
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unimport_jetty 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.40 urma_unimport_jetty_async 校验 目标 Jetty 无效导致导入流程拒绝继续执行
* 故障编号：urma_600
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unimport_jetty_async 在执行导入前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.41 urma_unimport_jetty_async 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_601
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unimport_jetty_async 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.42 urma_unimport_jetty_async 执行导入 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_602
* 故障现象：
    * 关键日志：匹配 Failed to unimport jetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unimport_jetty_async 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 5.43 urma_import_seg 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_603
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_seg 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.44 urma_import_seg 执行导入 segment 失败导致当前资源状态无法推进
* 故障编号：urma_604
* 故障现象：
    * 关键日志：匹配 Token value must be set when token policy is not URMA_TOKEN_NONE
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_seg 调用下层 provider、bond 组件或系统接口处理 segment 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 5.45 urma_import_seg 校验 context 无效导致导入流程拒绝继续执行
* 故障编号：urma_605
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_seg 在执行导入前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.46 urma_import_seg 执行导入 设备 失败导致当前资源状态无法推进
* 故障编号：urma_606
* 故障现象：
    * 关键日志：依次匹配 `[DRV_ERR]Failed to import seg, dev_name:`、`, eid_idx:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_import_seg 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 5.47 urma_unimport_seg 校验 目标 segment 无效导致导入流程拒绝继续执行
* 故障编号：urma_607
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unimport_seg 在执行导入前发现调用方传入的 目标 segment 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.48 urma_free_token_id 执行释放 token_id 失败导致当前资源状态无法推进
* 故障编号：urma_608
* 故障现象：
    * 关键日志：依次匹配 `ref:`、`, not zero`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_token_id 调用下层 provider、bond 组件或系统接口处理 token_id 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 5.49 urma_free_token_id 校验 context 无效导致释放流程拒绝继续执行
* 故障编号：urma_609
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_token_id 在执行释放前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.50 urma_free_token_id 执行释放 设备 失败导致当前资源状态无法推进
* 故障编号：urma_610
* 故障现象：
    * 关键日志：依次匹配 `[DRV_ERR]Failed to free token_id, dev_name:`、`, eid_idx:`、`, tid:`、`, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_token_id 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 5.51 urma_unregister_seg 校验 context 无效导致注册流程拒绝继续执行
* 故障编号：urma_611
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unregister_seg 在执行注册前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.52 urma_unregister_seg 校验 context 无效导致注册流程拒绝继续执行
* 故障编号：urma_612
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unregister_seg 在执行注册前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 5.53 urma_unregister_seg 执行注册 设备 失败导致当前资源状态无法推进
* 故障编号：urma_613
* 故障现象：
    * 关键日志：依次匹配 `[DRV_ERR]Unregister seg fail, dev_name:`、`, eid_idx:`、`, tid:`、`, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unregister_seg 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 5.54 urma_register_sysfs_dev 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_614
* 故障现象：
    * 关键日志：匹配 Register device failed. Failed to match driver for device
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_register_sysfs_dev 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
### 6 数据收发失败
* 故障编号：urma_615
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 6.1 bondp_rearm_jfc 校验 JFC 无效导致重挂流程拒绝继续执行
* 故障编号：urma_616
* 故障现象：
    * 关键日志：匹配 Invalid param
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_rearm_jfc 在执行重挂前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.2 bondp_rearm_jfc 执行重挂 JFCE 失败导致当前资源状态无法推进
* 故障编号：urma_617
* 故障现象：
    * 关键日志：匹配 Failed to rearm jfc: JFCE is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_rearm_jfc 调用下层 provider、bond 组件或系统接口处理 JFCE 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 6.3 bondp_wait_jfc 校验 JFCE 无效导致等待流程拒绝继续执行
* 故障编号：urma_618
* 故障现象：
    * 关键日志：匹配 Invalid param
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_wait_jfc 在执行等待前发现调用方传入的 JFCE 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.4 bondp_wait_jfc 管理 epoll fd 失败导致 JFCE 事件聚合不可用
* 故障编号：urma_619
* 故障现象：
    * 关键日志：匹配 v_jfce_table is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_wait_jfc 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll 系统调用失败，完成事件无法被统一监听和分发。
* 解决办法：无
#### 6.5 bondp_wait_jfc 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_620
* 故障现象：
    * 关键日志：匹配 `Epoll wait err, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_wait_jfc 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 6.6 bondp_get_async_event 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_621
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_get_async_event 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.7 bondp_get_async_event 管理 epoll fd 失败导致 JFCE 事件聚合不可用
* 故障编号：urma_622
* 故障现象：
    * 关键日志：匹配 epoll_wait no event or err
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_get_async_event 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll 系统调用失败，完成事件无法被统一监听和分发。
* 解决办法：无
#### 6.8 bondp_get_async_event 管理 epoll fd 失败导致 JFCE 事件聚合不可用
* 故障编号：urma_623
* 故障现象：
    * 关键日志：匹配 bondp get error epoll_event: 0x
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_get_async_event 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll 系统调用失败，完成事件无法被统一监听和分发。
* 解决办法：无
#### 6.9 bondp_get_async_event 校验 Jetty 无效导致获取流程拒绝继续执行
* 故障编号：urma_624
* 故障现象：
    * 关键日志：匹配 failed to get invalid jetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_get_async_event 在执行获取前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.10 bondp_ack_async_event 校验 异步事件 无效导致确认流程拒绝继续执行
* 故障编号：urma_625
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_ack_async_event 在执行确认前发现调用方传入的 异步事件 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.11 comp_post_send 校验 context 无效导致投递流程拒绝继续执行
* 故障编号：urma_626
* 故障现象：
    * 关键日志：匹配 Invalid post jfs wr type
    * 日志路径：URMA_LOG_PATH
* 故障原因：comp_post_send 在执行投递前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.12 comp_post_recv 校验 context 无效导致投递流程拒绝继续执行
* 故障编号：urma_627
* 故障现象：
    * 关键日志：匹配 Invalid post jfr wr type
    * 日志路径：URMA_LOG_PATH
* 故障原因：comp_post_recv 在执行投递前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.13 schedule_next_route_in_matrix_server_singlepath 校验 context 业务条件不满足导致调度流程拒绝继续执行
* 故障编号：urma_628
* 故障现象：
    * 关键日志：匹配 Invalid single path port. Single path mode only support RC and need to call bind_jetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：schedule_next_route_in_matrix_server_singlepath 在执行调度时发现 context 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 6.14 schedule_send 校验 目标 Jetty 无效导致发送流程拒绝继续执行
* 故障编号：urma_629
* 故障现象：
    * 关键日志：匹配 Invalid wr->tjetty: NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：schedule_send 在执行发送前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.15 set_send_wr_ptseg_ptjetty 执行设置 目标 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_630
* 故障现象：
    * 关键日志：匹配 tjetty in WR is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_send_wr_ptseg_ptjetty 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 6.16 set_send_wr_ptseg_ptjetty 校验 目标 Jetty 无效导致设置流程拒绝继续执行
* 故障编号：urma_631
* 故障现象：
    * 关键日志：匹配 Invalid vtjetty, the structure may be self-consturcted
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_send_wr_ptseg_ptjetty 在执行设置前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.17 set_send_wr_ptseg_ptjetty 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_632
* 故障现象：
    * 关键日志：匹配 Failed to set ptseg, vtseg is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：set_send_wr_ptseg_ptjetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 6.18 update_send_wr_before_post 执行投递 目标 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_633
* 故障现象：
    * 关键日志：匹配 Failed to set_jfs_wr_ptseg_ptjetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：update_send_wr_before_post 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 6.19 update_send_wr_before_post 执行投递 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_634
* 故障现象：
    * 关键日志：匹配 Failed to encode_jfs_wr_reliable_info
    * 日志路径：URMA_LOG_PATH
* 故障原因：update_send_wr_before_post 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 6.20 post_send_check_jfs_wr_valid 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_635
* 故障现象：
    * 关键日志：匹配 when set write_wr, either of src/dst num_sge/sge has been set zero or NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：post_send_check_jfs_wr_valid 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 6.21 post_send_check_jfs_wr_valid 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_636
* 故障现象：
    * 关键日志：匹配 when set cas_wr, either src or dst is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：post_send_check_jfs_wr_valid 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 6.22 post_send_check_jfs_wr_valid 执行投递 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_637
* 故障现象：
    * 关键日志：匹配 when set faa_wr, either src or dst is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：post_send_check_jfs_wr_valid 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 6.23 post_send_check_valid 校验 URMA 对象 无效导致投递流程拒绝继续执行
* 故障编号：urma_638
* 故障现象：
    * 关键日志：匹配 Invalid bdp_send_comp
    * 日志路径：URMA_LOG_PATH
* 故障原因：post_send_check_valid 在执行投递前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.24 post_send_check_valid 校验 Jetty 无效导致投递流程拒绝继续执行
* 故障编号：urma_639
* 故障现象：
    * 关键日志：匹配 Try to call post_send api by invalid comp_type
    * 日志路径：URMA_LOG_PATH
* 故障原因：post_send_check_valid 在执行投递前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.25 post_send_check_valid 校验 目标 Jetty 无效导致投递流程拒绝继续执行
* 故障编号：urma_640
* 故障现象：
    * 关键日志：匹配 Invalid bdp_target_jetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：post_send_check_valid 在执行投递前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.26 post_send_check_valid 校验 context 业务条件不满足导致投递流程拒绝继续执行
* 故障编号：urma_641
* 故障现象：
    * 关键日志：匹配 Data cannot be transferred between jettys in different matrix server mode
    * 日志路径：URMA_LOG_PATH
* 故障原因：post_send_check_valid 在执行投递时发现 context 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 6.27 post_send_check_valid 校验 目标 Jetty 业务条件不满足导致投递流程拒绝继续执行
* 故障编号：urma_642
* 故障现象：
    * 关键日志：匹配 Data cannot be transferred between jettys in different multipath mode
    * 日志路径：URMA_LOG_PATH
* 故障原因：post_send_check_valid 在执行投递时发现 目标 Jetty 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 6.28 post_send_check_valid 执行投递 context 失败导致当前资源状态无法推进
* 故障编号：urma_643
* 故障现象：
    * 关键日志：匹配 No bjetty_ctx
    * 日志路径：URMA_LOG_PATH
* 故障原因：post_send_check_valid 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 6.29 post_send_check_valid 校验 context 无效导致投递流程拒绝继续执行
* 故障编号：urma_644
* 故障现象：
    * 关键日志：匹配 All bonding devs are invalid
    * 日志路径：URMA_LOG_PATH
* 故障原因：post_send_check_valid 在执行投递前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.30 get_v_conn_on_send 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_645
* 故障现象：
    * 关键日志：匹配 `Failed to create vconn for (`
    * 日志路径：URMA_LOG_PATH
* 故障原因：get_v_conn_on_send 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 6.31 bondp_post_send_wr_no_store 执行投递 目标 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_646
* 故障现象：
    * 关键日志：匹配 WR->tjetty is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_post_send_wr_no_store 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 6.32 bondp_post_send_wr_no_store 执行投递 WR 失败导致当前资源状态无法推进
* 故障编号：urma_647
* 故障现象：
    * 关键日志：匹配 Bondp supports at most wr_list
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_post_send_wr_no_store 调用下层 provider、bond 组件或系统接口处理 WR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 6.33 schedule_next_recv_port_matrix_singlepath 校验 context 无效导致接收流程拒绝继续执行
* 故障编号：urma_648
* 故障现象：
    * 关键日志：匹配 Invalid single path port in recv.It is likely because `urma_post_jetty_recv` was called before `urma_bind_jetty`
    * 日志路径：URMA_LOG_PATH
* 故障原因：schedule_next_recv_port_matrix_singlepath 在执行接收前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.34 post_recv_check_valid 校验 URMA 对象 无效导致投递流程拒绝继续执行
* 故障编号：urma_649
* 故障现象：
    * 关键日志：匹配 Invalid bdp_comp
    * 日志路径：URMA_LOG_PATH
* 故障原因：post_recv_check_valid 在执行投递前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.35 post_recv_check_valid 执行投递 context 失败导致当前资源状态无法推进
* 故障编号：urma_650
* 故障现象：
    * 关键日志：匹配 bjetty_ctx is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：post_recv_check_valid 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 6.36 post_recv_check_valid 校验 Jetty 无效导致投递流程拒绝继续执行
* 故障编号：urma_651
* 故障现象：
    * 关键日志：匹配 Invalid bdp_recv_comp type
    * 日志路径：URMA_LOG_PATH
* 故障原因：post_recv_check_valid 在执行投递前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.37 send_so_from_snd_queue 执行发送 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_652
* 故障现象：
    * 关键日志：匹配 v_conn has NULL target_vjetty in sending SO
    * 日志路径：URMA_LOG_PATH
* 故障原因：send_so_from_snd_queue 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 6.38 resend_wr_from_node 执行发送 WR 失败导致当前资源状态无法推进
* 故障编号：urma_653
* 故障现象：
    * 关键日志：匹配 Unsupported send opcode
    * 日志路径：URMA_LOG_PATH
* 故障原因：resend_wr_from_node 调用下层 provider、bond 组件或系统接口处理 WR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 6.39 resend_wr_from_node 执行发送 目标 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_654
* 故障现象：
    * 关键日志：匹配 Failed to set ptseg_ptjetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：resend_wr_from_node 调用下层 provider、bond 组件或系统接口处理 目标 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 6.40 handle_send 校验 context 无效导致发送流程拒绝继续执行
* 故障编号：urma_655
* 故障现象：
    * 关键日志：匹配 Invalid bdp_comp type
    * 日志路径：URMA_LOG_PATH
* 故障原因：handle_send 在执行发送前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.41 handle_recv 校验 context 无效导致接收流程拒绝继续执行
* 故障编号：urma_656
* 故障现象：
    * 关键日志：匹配 Invalid bdp_comp type
    * 日志路径：URMA_LOG_PATH
* 故障原因：handle_recv 在执行接收前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.42 handle_recv 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_657
* 故障现象：
    * 关键日志：匹配 Failed to get target jetty id
    * 日志路径：URMA_LOG_PATH
* 故障原因：handle_recv 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 6.43 handle_recv 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_658
* 故障现象：
    * 关键日志：匹配 `Failed to create vconn for (`
    * 日志路径：URMA_LOG_PATH
* 故障原因：handle_recv 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 6.44 wait_async_event_ack 处理 context 异常导致当前 URMA 操作失败
* 故障编号：urma_659
* 故障现象：
    * 关键日志：依次匹配 `There is an event and it must be acked, acked:`、`, reported:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：wait_async_event_ack 在处理 context 的错误分支输出日志，表示当前对象或下层处理结果已经不能满足继续执行条件，因此返回错误并终止本次 URMA 操作。
* 解决办法：无
#### 6.45 urma_cmd_wait_jfc 校验 JFCE 无效导致等待流程拒绝继续执行
* 故障编号：urma_660
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_wait_jfc 在执行等待前发现调用方传入的 JFCE 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.46 urma_cmd_wait_jfc URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_661
* 故障现象：
    * 关键日志：依次匹配 `Faile to wait jfc non-block, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_wait_jfc 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。
* 解决办法：无
#### 6.47 urma_cmd_ack_jfc 校验 JFC 无效导致确认流程拒绝继续执行
* 故障编号：urma_662
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_ack_jfc 在执行确认前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.48 urma_cmd_get_async_event 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_663
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_get_async_event 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.49 urma_cmd_ack_async_event 校验 异步事件 无效导致确认流程拒绝继续执行
* 故障编号：urma_664
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_ack_async_event 在执行确认前发现调用方传入的 异步事件 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.50 urma_cmd_wait_notify 校验 fd 无效导致等待流程拒绝继续执行
* 故障编号：urma_665
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_wait_notify 在执行等待前发现调用方传入的 fd 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.51 urma_ioctl_wait_jfc 等待 JFC 完成事件 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_666
* 故障现象：
    * 关键日志：依次匹配 `wait jfc ioctl failed, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_ioctl_wait_jfc 通过 fd 向内核驱动下发等待 JFC 完成事件请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。
* 解决办法：无
#### 6.52 urma_ioctl_get_async_event 导入 Jetty ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_667
* 故障现象：
    * 关键日志：依次匹配 `get async event ioctl failed, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_ioctl_get_async_event 通过 fd 向内核驱动下发导入 Jetty请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 异步事件 状态。
* 解决办法：无
#### 6.53 urma_ioctl_wait_notify 查询 TP 列表 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_668
* 故障现象：
    * 关键日志：依次匹配 `wait notify ioctl failed, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_ioctl_wait_notify 通过 fd 向内核驱动下发查询 TP 列表请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 notify 事件 状态。
* 解决办法：无
#### 6.54 urma_wait_notify 校验 context 无效导致等待流程拒绝继续执行
* 故障编号：urma_669
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_wait_notify 在执行等待前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.55 urma_wait_notify 校验 context 无效导致等待流程拒绝继续执行
* 故障编号：urma_670
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_wait_notify 在执行等待前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.56 urma_wait_notify 校验 context 无效导致等待流程拒绝继续执行
* 故障编号：urma_671
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_wait_notify 在执行等待前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.57 urma_ack_notify 校验 context 无效导致确认流程拒绝继续执行
* 故障编号：urma_672
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_ack_notify 在执行确认前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.58 urma_ack_notify 校验 context 无效导致确认流程拒绝继续执行
* 故障编号：urma_673
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_ack_notify 在执行确认前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.59 urma_get_async_event 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_674
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_async_event 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.60 urma_get_async_event 校验 context 无效导致获取流程拒绝继续执行
* 故障编号：urma_675
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_get_async_event 在执行获取前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.61 urma_ack_async_event 校验 context 无效导致确认流程拒绝继续执行
* 故障编号：urma_676
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_ack_async_event 在执行确认前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.62 urma_ack_async_event 校验 异步事件 无效导致确认流程拒绝继续执行
* 故障编号：urma_677
* 故障现象：
    * 关键日志：匹配 Invalid parameter with ops nullptr
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_ack_async_event 在执行确认前发现调用方传入的 异步事件 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.63 urma_send 校验 JFR 无效导致发送流程拒绝继续执行
* 故障编号：urma_678
* 故障现象：
    * 关键日志：匹配 null pointer exists in tjfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_send 在执行发送前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.64 urma_send 校验 JFS 无效导致发送流程拒绝继续执行
* 故障编号：urma_679
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_send 在执行发送前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.65 urma_send 校验 目标 segment 无效导致发送流程拒绝继续执行
* 故障编号：urma_680
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_send 在执行发送前发现调用方传入的 目标 segment 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.66 urma_recv 校验 JFR 无效导致接收流程拒绝继续执行
* 故障编号：urma_681
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_recv 在执行接收前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.67 urma_recv 校验 JFR 无效导致接收流程拒绝继续执行
* 故障编号：urma_682
* 故障现象：
    * 关键日志：匹配 There are invalid parameters
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_recv 在执行接收前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.68 urma_poll_jfc 校验 JFC 无效导致轮询流程拒绝继续执行
* 故障编号：urma_683
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_poll_jfc 在执行轮询前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.69 urma_rearm_jfc 校验 JFC 无效导致重挂流程拒绝继续执行
* 故障编号：urma_684
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_rearm_jfc 在执行重挂前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.70 urma_wait_jfc 校验 JFC 无效导致等待流程拒绝继续执行
* 故障编号：urma_685
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_wait_jfc 在执行等待前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.71 urma_ack_jfc 校验 JFC 无效导致确认流程拒绝继续执行
* 故障编号：urma_686
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_ack_jfc 在执行确认前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.72 urma_ack_jfc 校验 JFC 无效导致确认流程拒绝继续执行
* 故障编号：urma_687
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_ack_jfc 在执行确认前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.73 urma_post_jfs_wr 校验 JFS 无效导致投递流程拒绝继续执行
* 故障编号：urma_688
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_post_jfs_wr 在执行投递前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.74 urma_post_jfr_wr 校验 JFR 无效导致投递流程拒绝继续执行
* 故障编号：urma_689
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_post_jfr_wr 在执行投递前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.75 urma_post_jetty_send_wr 校验 Jetty 无效导致投递流程拒绝继续执行
* 故障编号：urma_690
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_post_jetty_send_wr 在执行投递前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 6.76 urma_post_jetty_recv_wr 校验 Jetty 无效导致投递流程拒绝继续执行
* 故障编号：urma_691
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_post_jetty_recv_wr 在执行投递前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
### 7 资源销毁/清理失败
* 故障编号：urma_692
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 7.1 bondp_delete_jfce 执行删除 JFCE 失败导致当前资源状态无法推进
* 故障编号：urma_693
* 故障现象：
    * 关键日志：依次匹配 `Failed to delete jfce[`、`], still in use. use_cnt:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_jfce 调用下层 provider、bond 组件或系统接口处理 JFCE 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.2 bondp_delete_jfc 执行删除 JFC 失败导致当前资源状态无法推进
* 故障编号：urma_694
* 故障现象：
    * 关键日志：依次匹配 `Failed to delete jfc[`、`], still in use. use_cnt:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_jfc 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.3 bondp_delete_jfc 执行删除 JFC 失败导致当前资源状态无法推进
* 故障编号：urma_695
* 故障现象：
    * 关键日志：匹配 Failed to delete vjfc
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_jfc 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.4 bondp_delete_jfc 执行删除 JFC 失败导致当前资源状态无法推进
* 故障编号：urma_696
* 故障现象：
    * 关键日志：匹配 Failed to delete bdp_jfc
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_jfc 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.5 bondp_delete_pjfs 执行删除 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_697
* 故障现象：
    * 关键日志：依次匹配 `Failed to delete pjfs`、`, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_pjfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.6 bondp_delete_jfs 执行删除 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_698
* 故障现象：
    * 关键日志：依次匹配 `Failed to delete jfs[`、`], still in use. use_cnt:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.7 bondp_delete_jfs 执行删除 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_699
* 故障现象：
    * 关键日志：匹配 Failed to delete vjfs
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.8 bondp_delete_jfs 执行删除 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_700
* 故障现象：
    * 关键日志：匹配 Failed to delete pjfs
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.9 bondp_delete_pjfr 执行删除 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_701
* 故障现象：
    * 关键日志：依次匹配 `Failed to delete pjfr`、`, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_pjfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.10 bondp_delete_jfr 执行删除 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_702
* 故障现象：
    * 关键日志：依次匹配 `Failed to delete jfr[`、`], still in use. use_cnt:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.11 bondp_delete_jfr 执行删除 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_703
* 故障现象：
    * 关键日志：匹配 Failed to delete_vjfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.12 bondp_delete_jfr 执行删除 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_704
* 故障现象：
    * 关键日志：匹配 Failed to delete pjfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.13 bondp_delete_pjetty 执行删除 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_705
* 故障现象：
    * 关键日志：依次匹配 `Failed to delete pjetty`、`, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_pjetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.14 bondp_delete_jetty 执行删除 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_706
* 故障现象：
    * 关键日志：依次匹配 `Failed to delete jetty[`、`], still in use. use_cnt:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.15 bondp_delete_jetty 执行删除 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_707
* 故障现象：
    * 关键日志：匹配 Failed to delete vjetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.16 bondp_delete_jetty 执行删除 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_708
* 故障现象：
    * 关键日志：匹配 Failed to delete pjetty
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.17 remove_remote_jetty_id_info 执行处理 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_709
* 故障现象：
    * 关键日志：依次匹配 `Failed to del bdp_r_p2v_vjetty_id[`、`]: ret:`、`, jetty_id: (`、`, uasid:`、`, id:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：remove_remote_jetty_id_info 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.18 bondp_remove_p_jfce 管理 epoll fd 失败导致 JFCE 事件聚合不可用
* 故障编号：urma_710
* 故障现象：
    * 关键日志：匹配 Fail to del fd: to epoll fd
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_remove_p_jfce 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll 系统调用失败，完成事件无法被统一监听和分发。
* 解决办法：无
#### 7.19 bondp_delete_comp_jfce 执行删除 JFCE 失败导致当前资源状态无法推进
* 故障编号：urma_711
* 故障现象：
    * 关键日志：匹配 `Failed to delete p_jfce, ret =`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_comp_jfce 调用下层 provider、bond 组件或系统接口处理 JFCE 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.20 bondp_delete_comp_default 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_712
* 故障现象：
    * 关键日志：匹配 Failed to delete comp type
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_comp_default 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 7.21 bondp_delete_comp_default 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_713
* 故障现象：
    * 关键日志：匹配 `Fail to uninit comp attr, ret`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_comp_default 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 7.22 bondp_delete_comp 校验 URMA 对象 无效导致删除流程拒绝继续执行
* 故障编号：urma_714
* 故障现象：
    * 关键日志：匹配 Invalid param
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_comp 在执行删除前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.23 bondp_delete_context 执行删除 context 失败导致当前资源状态无法推进
* 故障编号：urma_715
* 故障现象：
    * 关键日志：匹配 Failed to delete context
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_context 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.24 bondp_delete_context 执行删除 context 失败导致当前资源状态无法推进
* 故障编号：urma_716
* 故障现象：
    * 关键日志：匹配 Failed to urma_cmd_delete_context
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_context 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.25 bondp_delete_pseg 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_717
* 故障现象：
    * 关键日志：匹配 Failed to unregister pseg
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_pseg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 7.26 bondp_delete_vseg 校验 segment 无效导致删除流程拒绝继续执行
* 故障编号：urma_718
* 故障现象：
    * 关键日志：匹配 invalid param
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_vseg 在执行删除前发现调用方传入的 segment 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.27 bondp_delete_vseg 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_719
* 故障现象：
    * 关键日志：依次匹配 `Failed to unregister segment, token_id:`、`, handle:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_delete_vseg 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 7.28 delete_copied_jfs_wr_node 校验 JFS 业务条件不满足导致删除流程拒绝继续执行
* 故障编号：urma_720
* 故障现象：
    * 关键日志：匹配 `Not support opcode`
    * 日志路径：URMA_LOG_PATH
* 故障原因：delete_copied_jfs_wr_node 在执行删除时发现 JFS 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 7.29 delete_copied_jfs_wr 校验 JFS 无效导致删除流程拒绝继续执行
* 故障编号：urma_721
* 故障现象：
    * 关键日志：匹配 Invalid jfs wr to delete
    * 日志路径：URMA_LOG_PATH
* 故障原因：delete_copied_jfs_wr 在执行删除前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.30 delete_copied_jfr_wr_node 校验 JFR 无效导致删除流程拒绝继续执行
* 故障编号：urma_722
* 故障现象：
    * 关键日志：匹配 Invalid jfr wr to delete
    * 日志路径：URMA_LOG_PATH
* 故障原因：delete_copied_jfr_wr_node 在执行删除前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.31 delete_copied_jfr_wr 校验 JFR 无效导致删除流程拒绝继续执行
* 故障编号：urma_723
* 故障现象：
    * 关键日志：匹配 Invalid jfr wr to delete
    * 日志路径：URMA_LOG_PATH
* 故障原因：delete_copied_jfr_wr 在执行删除前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.32 urma_cmd_delete_context 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_724
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_context 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.33 urma_cmd_delete_jfs 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_725
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfs 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.34 urma_cmd_delete_jfs URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_726
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfs 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFS 状态。
* 解决办法：无
#### 7.35 urma_cmd_delete_jfs_batch 校验 JFS 无效导致删除流程拒绝继续执行
* 故障编号：urma_727
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfs_batch 在执行删除前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.36 urma_cmd_delete_jfs_batch 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_728
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfs_batch 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.37 urma_cmd_delete_jfs_batch URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_729
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_delete_jfs_batch , ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfs_batch 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFS 状态。
* 解决办法：无
#### 7.38 urma_cmd_delete_jfs_batch 校验 JFS 业务条件不满足导致删除流程拒绝继续执行
* 故障编号：urma_730
* 故障现象：
    * 关键日志：匹配 `bad jfs index exceed array length, bad_jfs_index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfs_batch 在执行删除时发现 JFS 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 7.39 urma_cmd_free_jfs URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_731
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_free_jfs , ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_free_jfs 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFS 状态。
* 解决办法：无
#### 7.40 urma_cmd_delete_jfr 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_732
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfr 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.41 urma_cmd_delete_jfr URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_733
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_delete_jfr, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfr 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFR 状态。
* 解决办法：无
#### 7.42 urma_cmd_delete_jfr_batch 校验 JFR 无效导致删除流程拒绝继续执行
* 故障编号：urma_734
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfr_batch 在执行删除前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.43 urma_cmd_delete_jfr_batch 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_735
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfr_batch 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.44 urma_cmd_delete_jfr_batch URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_736
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_delete_jfr_batch , ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfr_batch 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFR 状态。
* 解决办法：无
#### 7.45 urma_cmd_delete_jfr_batch 校验 JFR 业务条件不满足导致删除流程拒绝继续执行
* 故障编号：urma_737
* 故障现象：
    * 关键日志：匹配 `bad jfr index exceed array length, bad_jfr_index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfr_batch 在执行删除时发现 JFR 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 7.46 urma_cmd_delete_jfc 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_738
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfc 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.47 urma_cmd_delete_jfc URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_739
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_delete_jfc , ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfc 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。
* 解决办法：无
#### 7.48 urma_cmd_delete_jfc URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_740
* 故障现象：
    * 关键日志：依次匹配 `There is jfc event and it must be acked, jfc_comp:`、`, comp:`、`, jfc_async:`、`, async:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfc 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。
* 解决办法：无
#### 7.49 urma_cmd_delete_jfc_batch 校验 JFC 无效导致删除流程拒绝继续执行
* 故障编号：urma_741
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfc_batch 在执行删除前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.50 urma_cmd_delete_jfc_batch 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_742
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfc_batch 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.51 urma_cmd_delete_jfc_batch URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_743
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_delete_jfc_batch , ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfc_batch 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。
* 解决办法：无
#### 7.52 urma_cmd_delete_jfc_batch 校验 JFC 业务条件不满足导致删除流程拒绝继续执行
* 故障编号：urma_744
* 故障现象：
    * 关键日志：匹配 `bad jfc index exceed array length, bad_jfc_index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jfc_batch 在执行删除时发现 JFC 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 7.53 urma_cmd_free_jfc URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_745
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_delete_jfc , ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_free_jfc 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。
* 解决办法：无
#### 7.54 urma_cmd_free_jfc URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_746
* 故障现象：
    * 关键日志：依次匹配 `There is jfc event and it must be acked, jfc_comp:`、`, comp:`、`, jfc_async:`、`, async:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_free_jfc 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。
* 解决办法：无
#### 7.55 urma_cmd_free_jfr URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_747
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_delete_jfr , ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_free_jfr 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFR 状态。
* 解决办法：无
#### 7.56 urma_cmd_delete_jetty 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_748
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jetty 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.57 urma_cmd_delete_jetty URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_749
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jetty 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 Jetty 状态。
* 解决办法：无
#### 7.58 urma_cmd_delete_jetty_batch 校验 Jetty 无效导致删除流程拒绝继续执行
* 故障编号：urma_750
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jetty_batch 在执行删除前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.59 urma_cmd_delete_jetty_batch 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_751
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jetty_batch 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.60 urma_cmd_delete_jetty_batch URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_752
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_delete_jetty_batch , ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jetty_batch 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 Jetty 状态。
* 解决办法：无
#### 7.61 urma_cmd_delete_jetty_batch 校验 Jetty 业务条件不满足导致删除流程拒绝继续执行
* 故障编号：urma_753
* 故障现象：
    * 关键日志：匹配 `bad jetty index exceed array length, bad_jetty_index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jetty_batch 在执行删除时发现 Jetty 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 7.62 urma_cmd_delete_jetty_grp 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_754
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_delete_jetty_grp 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.63 urma_cmd_free_jetty URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_755
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_free_jetty 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 Jetty 状态。
* 解决办法：无
#### 7.64 urma_free_jfc 校验 JFC 无效导致释放流程拒绝继续执行
* 故障编号：urma_756
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jfc 在执行释放前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.65 urma_free_jfc 执行释放 JFC 失败导致当前资源状态无法推进
* 故障编号：urma_757
* 故障现象：
    * 关键日志：匹配 jfc still actived, please deactived first
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jfc 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.66 urma_free_jfc 校验 context 无效导致释放流程拒绝继续执行
* 故障编号：urma_758
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jfc 在执行释放前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.67 urma_delete_jfc 校验 JFC 无效导致删除流程拒绝继续执行
* 故障编号：urma_759
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfc 在执行删除前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.68 urma_delete_jfc 执行删除 JFC 失败导致当前资源状态无法推进
* 故障编号：urma_760
* 故障现象：
    * 关键日志：匹配 jfc is deactived, can not delete
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfc 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.69 urma_delete_jfc 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_761
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfc 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.70 urma_delete_jfc 执行删除 设备 失败导致当前资源状态无法推进
* 故障编号：urma_762
* 故障现象：
    * 关键日志：依次匹配 `[DRV_ERR]Failed to delete jfc, dev_name:`、`, eid_idx:`、`, id:`、`, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfc 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.71 urma_delete_jfc_batch 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_763
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfc_batch 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.72 urma_free_jfs 校验 JFS 无效导致释放流程拒绝继续执行
* 故障编号：urma_764
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jfs 在执行释放前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.73 urma_free_jfs 执行释放 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_765
* 故障现象：
    * 关键日志：匹配 jfs still actived, please deactived first
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.74 urma_free_jfs 校验 context 无效导致释放流程拒绝继续执行
* 故障编号：urma_766
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jfs 在执行释放前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.75 urma_free_jfs 执行释放 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_767
* 故障现象：
    * 关键日志：匹配 Failed to free jfs
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.76 urma_delete_jfs 校验 JFS 无效导致删除流程拒绝继续执行
* 故障编号：urma_768
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfs 在执行删除前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.77 urma_delete_jfs 执行删除 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_769
* 故障现象：
    * 关键日志：匹配 jfs is deactived, can not delete
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.78 urma_delete_jfs 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_770
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfs 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.79 urma_delete_jfs 执行删除 设备 失败导致当前资源状态无法推进
* 故障编号：urma_771
* 故障现象：
    * 关键日志：依次匹配 `[DRV_ERR]Failed to delete jfs, dev_name:`、`, eid_idx:`、`, id:`、`, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfs 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.80 urma_delete_jfs_batch 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_772
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfs_batch 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.81 urma_delete_jfs_batch 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_773
* 故障现象：
    * 关键日志：匹配 Failed to delete jfs batch
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfs_batch 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 7.82 urma_free_jfr 校验 JFR 无效导致释放流程拒绝继续执行
* 故障编号：urma_774
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jfr 在执行释放前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.83 urma_free_jfr 执行释放 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_775
* 故障现象：
    * 关键日志：匹配 jfr still actived, please deactived first
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.84 urma_free_jfr 校验 context 无效导致释放流程拒绝继续执行
* 故障编号：urma_776
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jfr 在执行释放前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.85 urma_free_jfr 执行释放 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_777
* 故障现象：
    * 关键日志：匹配 Failed to free jfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.86 urma_delete_jfr 校验 JFR 无效导致删除流程拒绝继续执行
* 故障编号：urma_778
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfr 在执行删除前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.87 urma_delete_jfr 执行删除 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_779
* 故障现象：
    * 关键日志：匹配 jfr is deactived, can not delete
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.88 urma_delete_jfr 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_780
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfr 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.89 urma_delete_jfr 执行删除 设备 失败导致当前资源状态无法推进
* 故障编号：urma_781
* 故障现象：
    * 关键日志：依次匹配 `[DRV_ERR]Failed to delete jfr, dev_name:`、`, eid_idx:`、`, id:`、`, status:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfr 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.90 urma_delete_jfr_batch 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_782
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfr_batch 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.91 urma_delete_jfr_batch 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_783
* 故障现象：
    * 关键日志：匹配 Failed to delete jfr batch
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfr_batch 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 7.92 urma_delete_jfce 校验 JFCE 无效导致删除流程拒绝继续执行
* 故障编号：urma_784
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfce 在执行删除前发现调用方传入的 JFCE 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：当前不会触发
#### 7.93 urma_delete_jfce 执行删除 JFCE 失败导致当前资源状态无法推进
* 故障编号：urma_785
* 故障现象：
    * 关键日志：匹配 `Jfce is still used by at least one jfc, refcnt:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfce 调用下层 provider、bond 组件或系统接口处理 JFCE 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：当前不会触发
#### 7.94 urma_delete_jfce 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_786
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfce 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：当前不会触发
#### 7.95 urma_delete_jfce 执行删除 JFCE 失败导致当前资源状态无法推进
* 故障编号：urma_787
* 故障现象：
    * 关键日志：匹配 `[DRV_ERR]Failed to delete jfce, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jfce 调用下层 provider、bond 组件或系统接口处理 JFCE 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：当前不会触发
#### 7.96 urma_delete_jetty_to_jetty_grp 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_788
* 故障现象：
    * 关键日志：匹配 failed to delete jetty to jetty_grp
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty_to_jetty_grp 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 7.97 urma_free_jetty 校验 Jetty 无效导致释放流程拒绝继续执行
* 故障编号：urma_789
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jetty 在执行释放前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.98 urma_free_jetty 执行释放 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_790
* 故障现象：
    * 关键日志：匹配 jetty still actived, please deactived first
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.99 urma_free_jetty 执行释放 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_791
* 故障现象：
    * 关键日志：匹配 Failed to delete jetty because it has remote jetty, try unbind first
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.100 urma_free_jetty 校验 context 无效导致释放流程拒绝继续执行
* 故障编号：urma_792
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_free_jetty 在执行释放前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.101 urma_delete_jetty 校验 Jetty 无效导致删除流程拒绝继续执行
* 故障编号：urma_793
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty 在执行删除前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.102 urma_delete_jetty 执行删除 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_794
* 故障现象：
    * 关键日志：匹配 jetty still deactived, can not delete
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.103 urma_delete_jetty 执行删除 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_795
* 故障现象：
    * 关键日志：匹配 Failed to delete jetty because it has remote jetty, try unbind first
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.104 urma_delete_jetty 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_796
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.105 urma_delete_jetty 执行删除 设备 失败导致当前资源状态无法推进
* 故障编号：urma_797
* 故障现象：
    * 关键日志：依次匹配 `[DRV_ERR]Failed to delete jetty, dev_name:`、`, eid_idx:`、`, id:`、`, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.106 urma_delete_jetty_batch 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_798
* 故障现象：
    * 关键日志：匹配 `Failed to delete as jetty has remote jetty, try unbind, index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty_batch 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 7.107 urma_delete_jetty_batch 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_799
* 故障现象：
    * 关键日志：匹配 `Invalid parameter, index:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty_batch 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.108 urma_delete_jetty_batch 执行删除 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_800
* 故障现象：
    * 关键日志：匹配 `Failed to delete jetty batch, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty_batch 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.109 urma_delete_notifier 校验 URMA 对象 无效导致删除流程拒绝继续执行
* 故障编号：urma_801
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_notifier 在执行删除前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.110 urma_delete_notifier 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_802
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_notifier 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.111 urma_delete_notifier 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_803
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_notifier 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.112 urma_delete_notifier 执行删除 URMA 对象 失败导致当前资源状态无法推进
* 故障编号：urma_804
* 故障现象：
    * 关键日志：匹配 `Failed to delete notifier, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_notifier 调用下层 provider、bond 组件或系统接口处理 URMA 对象 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.113 urma_delete_jetty_grp 校验 Jetty 无效导致删除流程拒绝继续执行
* 故障编号：urma_805
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty_grp 在执行删除前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.114 urma_delete_jetty_grp 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_806
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty_grp 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.115 urma_delete_jetty_grp 校验 Jetty 无效导致删除流程拒绝继续执行
* 故障编号：urma_807
* 故障现象：
    * 关键日志：匹配 Invalid parameter: jetty_list
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty_grp 在执行删除前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 7.116 urma_delete_jetty_grp 执行删除 Jetty group 失败导致当前资源状态无法推进
* 故障编号：urma_808
* 故障现象：
    * 关键日志：匹配 jetty grp in use, jetty_cnt
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_jetty_grp 调用下层 provider、bond 组件或系统接口处理 Jetty group 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 7.117 urma_delete_context 校验 context 无效导致删除流程拒绝继续执行
* 故障编号：urma_809
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_delete_context 在执行删除前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：当前不会触发
### 8 设备/驱动交互失败
* 故障编号：urma_810
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 8.1 urma_cmd_modify_jfs 校验 context 无效导致修改流程拒绝继续执行
* 故障编号：urma_811
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_modify_jfs 在执行修改前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 8.2 urma_cmd_modify_jfs URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_812
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_modify_jfs, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_modify_jfs 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFS 状态。
* 解决办法：无
#### 8.3 urma_cmd_modify_jfr 校验 context 无效导致修改流程拒绝继续执行
* 故障编号：urma_813
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_modify_jfr 在执行修改前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 8.4 urma_cmd_modify_jfr URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_814
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_modify_jfr, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_modify_jfr 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFR 状态。
* 解决办法：无
#### 8.5 urma_cmd_modify_jfc 校验 context 无效导致修改流程拒绝继续执行
* 故障编号：urma_815
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_modify_jfc 在执行修改前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 8.6 urma_cmd_modify_jfc URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断
* 故障编号：urma_816
* 故障现象：
    * 关键日志：依次匹配 `ioctl failed in urma_cmd_modify_jfc, ret:`、`, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_modify_jfc 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl 返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。
* 解决办法：无
#### 8.7 urma_cmd_advise_jfr 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_817
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_advise_jfr 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 8.8 urma_cmd_unadvise_jfr 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_818
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_unadvise_jfr 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 8.9 urma_cmd_unadvise_jetty 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_819
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_unadvise_jetty 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 8.10 urma_cmd_modify_jetty 校验 context 无效导致修改流程拒绝继续执行
* 故障编号：urma_820
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_modify_jetty 在执行修改前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 8.11 urma_check_jetty_cfg_with_jetty_grp 校验 Jetty 无效导致校验流程拒绝继续执行
* 故障编号：urma_821
* 故障现象：
    * 关键日志：匹配 Invalid token with unshared jfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_check_jetty_cfg_with_jetty_grp 在执行校验前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 8.12 urma_add_jetty_to_jetty_grp 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_822
* 故障现象：
    * 关键日志：匹配 failed to add jetty to jetty_grp
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_add_jetty_to_jetty_grp 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 8.13 urma_discover_devices 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_823
* 故障现象：
    * 关键日志：匹配 `open failed, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_discover_devices 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
#### 8.14 urma_close_provider 打开 provider 失败导致处理无法访问底层资源
* 故障编号：urma_824
* 故障现象：
    * 关键日志：匹配 close failed, err
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_close_provider 需要访问 provider 对应的文件、目录、provider 动态库或字符设备，但路径不存在、权限不足或系统调用失败，导致后续 URMA 设备枚举、provider 装载或上下文创建无法进行。
* 解决办法：无
#### 8.15 urma_validate_driver 校验 URMA 对象 无效导致处理流程拒绝继续执行
* 故障编号：urma_825
* 故障现象：
    * 关键日志：匹配 Invalid driver name length
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_validate_driver 在执行处理前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 8.16 urma_open_drivers 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_826
* 故障现象：
    * 关键日志：匹配 Failed to get dl addr
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_open_drivers 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 8.17 urma_open_drivers 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_827
* 故障现象：
    * 关键日志：匹配 Failed to prepare dli_fname
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_open_drivers 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 8.18 urma_open_drivers 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_828
* 故障现象：
    * 关键日志：依次匹配 `strrchr`、`failed, errno:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_open_drivers 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 8.19 urma_open_drivers 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_829
* 故障现象：
    * 关键日志：匹配 Failed to open liburma dir
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_open_drivers 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 8.20 urma_open_drivers 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_830
* 故障现象：
    * 关键日志：依次匹配 `snprintf_s`、`failed`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_open_drivers 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 8.21 urma_open_drivers 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_831
* 故障现象：
    * 关键日志：匹配 Failed to open provider
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_open_drivers 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 8.22 urma_open_cdev 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用
* 故障编号：urma_832
* 故障现象：
    * 关键日志：依次匹配 `file_path:`、`is not standardize`
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_open_cdev 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA 设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID 信息无法被用户态正确使用。
* 解决办法：无
### 9 其他URMA故障
* 故障编号：urma_833
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决办法：向下级匹配。
#### 9.1 bondp_modify_jfc 执行修改 JFC 失败导致当前资源状态无法推进
* 故障编号：urma_834
* 故障现象：
    * 关键日志：依次匹配 `modify pjfc fail, index:`、`, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_modify_jfc 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.2 bondp_add_jfs_p_vjetty_id_info 执行处理 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_835
* 故障现象：
    * 关键日志：依次匹配 `Failed to add p_vjfs_id[`、`]: ret:`、`, p_jfs_id:`、`, v_jfs_id:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_add_jfs_p_vjetty_id_info 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.3 bondp_del_jfs_p_vjetty_info_without_lock 执行处理 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_836
* 故障现象：
    * 关键日志：依次匹配 `Failed to delete p_vjfs_id node[`、`]: ret:`、`pjfs_id:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_del_jfs_p_vjetty_info_without_lock 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.4 bondp_modify_jfs 执行修改 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_837
* 故障现象：
    * 关键日志：依次匹配 `modify pjfs fail, index:`、`, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_modify_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.5 bondp_add_jfr_p_vjetty_id_info 执行处理 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_838
* 故障现象：
    * 关键日志：依次匹配 `Failed to add p_vjfr_id[`、`]: ret:`、`, p_jfr_id:`、`, v_jfr_id:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_add_jfr_p_vjetty_id_info 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.6 bondp_del_jfr_p_vjetty_info_without_lock 执行处理 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_839
* 故障现象：
    * 关键日志：依次匹配 `Failed to delete p_vjfr_id node[`、`]: ret`、`pjfr_id:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_del_jfr_p_vjetty_info_without_lock 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.7 bondp_modify_jfr 执行修改 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_840
* 故障现象：
    * 关键日志：依次匹配 `modify pjfr fail, index:`、`, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_modify_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.8 bondp_add_jetty_p_vjetty_id_info 执行处理 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_841
* 故障现象：
    * 关键日志：依次匹配 `Failed to add p_vjetty_id[`、`]: ret:`、`, p_jetty_id:`、`, v_jetty_id:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_add_jetty_p_vjetty_id_info 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.9 bondp_del_jetty_p_vjetty_info_without_lock 执行处理 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_842
* 故障现象：
    * 关键日志：依次匹配 `Failed to delete p_vjetty_id node: ret:`、`pjetty_id:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_del_jetty_p_vjetty_info_without_lock 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.10 bondp_modify_jetty 执行修改 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_843
* 故障现象：
    * 关键日志：依次匹配 `modify pjetty fail, index:`、`, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_modify_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.11 bondp_user_ctl 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_844
* 故障现象：
    * 关键日志：匹配 Invalid len
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_user_ctl 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.12 bondp_user_ctl 执行处理 context 失败导致当前资源状态无法推进
* 故障编号：urma_845
* 故障现象：
    * 关键日志：匹配 `Unsupported opcode, opcode:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_user_ctl 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.13 add_remote_jetty_id_info 执行处理 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_846
* 故障现象：
    * 关键日志：依次匹配 `Failed to add bdp_r_p2v_vjetty_id[`、`]: ret:`、`, jetty_id: (`、`, uasid:`、`, id:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：add_remote_jetty_id_info 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.14 bondp_insert_p_jfce 管理 epoll fd 失败导致 JFCE 事件聚合不可用
* 故障编号：urma_847
* 故障现象：
    * 关键日志：依次匹配 `Fail to add fd:`、`to epoll fd`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_insert_p_jfce 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll 系统调用失败，完成事件无法被统一监听和分发。
* 解决办法：无
#### 9.15 BDP_V_CONN_HASH_BASIS 校验 Jetty 无效导致处理流程拒绝继续执行
* 故障编号：urma_848
* 故障现象：
    * 关键日志：匹配 Invalid param
    * 日志路径：URMA_LOG_PATH
* 故障原因：BDP_V_CONN_HASH_BASIS 在执行处理前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.16 encode_jfs_wr_reliable_info 执行处理 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_849
* 故障现象：
    * 关键日志：匹配 Unsupported send opcode
    * 日志路径：URMA_LOG_PATH
* 故障原因：encode_jfs_wr_reliable_info 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.17 restore_cr_local_id 执行处理 Jetty 失败导致当前资源状态无法推进
* 故障编号：urma_850
* 故障现象：
    * 关键日志：依次匹配 `Failed to get vjetty.id of local_id:`、`, ret:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：restore_cr_local_id 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.18 bondp_handle_cr_no_store 校验 WR 无效导致处理流程拒绝继续执行
* 故障编号：urma_851
* 故障现象：
    * 关键日志：匹配 `Invalid cr error status:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_handle_cr_no_store 在执行处理前发现调用方传入的 WR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.19 bondp_flush_jetty 装载或匹配 provider 失败导致设备驱动能力不可用
* 故障编号：urma_852
* 故障现象：
    * 关键日志：依次匹配 `Failed to flush pjetty[`、`]:`
    * 日志路径：URMA_LOG_PATH
* 故障原因：bondp_flush_jetty 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。
* 解决办法：无
#### 9.20 bdp_queue_front 执行处理 URMA 对象 失败导致当前资源状态无法推进
* 故障编号：urma_853
* 故障现象：
    * 关键日志：匹配 data is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_queue_front 调用下层 provider、bond 组件或系统接口处理 URMA 对象 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.21 bdp_queue_pop_head 执行处理 URMA 对象 失败导致当前资源状态无法推进
* 故障编号：urma_854
* 故障现象：
    * 关键日志：匹配 data is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_queue_pop_head 调用下层 provider、bond 组件或系统接口处理 URMA 对象 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.22 bdp_queue_pop_tail 执行处理 URMA 对象 失败导致当前资源状态无法推进
* 故障编号：urma_855
* 故障现象：
    * 关键日志：匹配 data is NULL
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_queue_pop_tail 调用下层 provider、bond 组件或系统接口处理 URMA 对象 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.23 bdp_slide_wnd_seq_in_window 校验 URMA 对象 无效导致处理流程拒绝继续执行
* 故障编号：urma_856
* 故障现象：
    * 关键日志：匹配 Invalid param wnd
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_slide_wnd_seq_in_window 在执行处理前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.24 bdp_slide_wnd_seq_in_window 更新 URMA 对象 映射结构失败导致资源索引不可用
* 故障编号：urma_857
* 故障现象：
    * 关键日志：匹配 Seq larger than total size of bitmap
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_slide_wnd_seq_in_window 需要维护 URMA 对象 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 9.25 bdp_slide_wnd_has 校验 URMA 对象 无效导致处理流程拒绝继续执行
* 故障编号：urma_858
* 故障现象：
    * 关键日志：匹配 Invalid param wnd
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_slide_wnd_has 在执行处理前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.26 bdp_slide_wnd_has 更新 URMA 对象 映射结构失败导致资源索引不可用
* 故障编号：urma_859
* 故障现象：
    * 关键日志：匹配 Seq larger than total size of bitmap
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_slide_wnd_has 需要维护 URMA 对象 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 9.27 bdp_slide_wnd_add 校验 URMA 对象 无效导致处理流程拒绝继续执行
* 故障编号：urma_860
* 故障现象：
    * 关键日志：匹配 Invalid param wnd
    * 日志路径：URMA_LOG_PATH
* 故障原因：bdp_slide_wnd_add 在执行处理前发现调用方传入的 URMA 对象 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.28 update_mapping_hash_table 更新 设备 映射结构失败导致资源索引不可用
* 故障编号：urma_861
* 故障现象：
    * 关键日志：匹配 Failed to add agg eid to mapping hash table
    * 日志路径：URMA_LOG_PATH
* 故障原因：update_mapping_hash_table 需要维护 设备 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 9.29 update_mapping_hash_table 更新 设备 映射结构失败导致资源索引不可用
* 故障编号：urma_862
* 故障现象：
    * 关键日志：匹配 Failed to add primary eid to mapping hash table
    * 日志路径：URMA_LOG_PATH
* 故障原因：update_mapping_hash_table 需要维护 设备 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 9.30 update_mapping_hash_table 更新 设备 映射结构失败导致资源索引不可用
* 故障编号：urma_863
* 故障现象：
    * 关键日志：匹配 Failed to add port eid to mapping hash table
    * 日志路径：URMA_LOG_PATH
* 故障原因：update_mapping_hash_table 需要维护 设备 到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。
* 解决办法：无
#### 9.31 deepcopy_jfs_wr_node 执行复制 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_864
* 故障现象：
    * 关键日志：匹配 Deepcopy src sg failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_jfs_wr_node 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.32 deepcopy_jfs_wr_node 执行复制 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_865
* 故障现象：
    * 关键日志：匹配 Deepcopy dst sg failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_jfs_wr_node 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.33 deepcopy_jfs_wr_node 执行复制 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_866
* 故障现象：
    * 关键日志：匹配 Deepcopy cas failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_jfs_wr_node 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.34 deepcopy_jfs_wr_node 执行复制 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_867
* 故障现象：
    * 关键日志：匹配 Deepcopy faa failed
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_jfs_wr_node 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.35 deepcopy_jfs_wr_node 校验 JFS 业务条件不满足导致复制流程拒绝继续执行
* 故障编号：urma_868
* 故障现象：
    * 关键日志：匹配 `Not support opcode`
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_jfs_wr_node 在执行复制时发现 JFS 的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资源关系或下发不被支持的请求。
* 解决办法：无
#### 9.36 deepcopy_jfs_wr_inner 校验 JFS 无效导致复制流程拒绝继续执行
* 故障编号：urma_869
* 故障现象：
    * 关键日志：匹配 Invalid jfs wr to deepcopy
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_jfs_wr_inner 在执行复制前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.37 deepcopy_jfs_wr_inner 执行复制 JFS 失败导致当前资源状态无法推进
* 故障编号：urma_870
* 故障现象：
    * 关键日志：匹配 Failed to copy in wr->next
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_jfs_wr_inner 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.38 deepcopy_jfr_wr_inner 校验 JFR 无效导致复制流程拒绝继续执行
* 故障编号：urma_871
* 故障现象：
    * 关键日志：匹配 Invalid jfr wr to deepcopy
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_jfr_wr_inner 在执行复制前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.39 deepcopy_jfr_wr_inner 执行复制 JFR 失败导致当前资源状态无法推进
* 故障编号：urma_872
* 故障现象：
    * 关键日志：匹配 Failed to copy in wr->next
    * 日志路径：URMA_LOG_PATH
* 故障原因：deepcopy_jfr_wr_inner 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.40 urma_cmd_user_ctl 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_873
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_cmd_user_ctl 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.41 urma_check_opt_valid 校验 映射表 无效导致校验流程拒绝继续执行
* 故障编号：urma_874
* 故障现象：
    * 关键日志：匹配 invalid opt len
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_check_opt_valid 在执行校验前发现调用方传入的 映射表 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.42 urma_modify_jfc 校验 JFC 无效导致修改流程拒绝继续执行
* 故障编号：urma_875
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_modify_jfc 在执行修改前发现调用方传入的 JFC 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.43 urma_modify_jfc 校验 context 无效导致修改流程拒绝继续执行
* 故障编号：urma_876
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_modify_jfc 在执行修改前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.44 urma_modify_jfs 校验 JFS 无效导致修改流程拒绝继续执行
* 故障编号：urma_877
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_modify_jfs 在执行修改前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.45 urma_modify_jfs 校验 context 无效导致修改流程拒绝继续执行
* 故障编号：urma_878
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_modify_jfs 在执行修改前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.46 urma_modify_jfr 校验 JFR 无效导致修改流程拒绝继续执行
* 故障编号：urma_879
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_modify_jfr 在执行修改前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.47 urma_modify_jfr 校验 context 无效导致修改流程拒绝继续执行
* 故障编号：urma_880
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_modify_jfr 在执行修改前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.48 urma_check_jetty_cfg_with_jetty_grp 校验 Jetty 无效导致校验流程拒绝继续执行
* 故障编号：urma_881
* 故障现象：
    * 关键日志：匹配 Invalid token with share_jfr
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_check_jetty_cfg_with_jetty_grp 在执行校验前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.49 urma_modify_jetty 校验 Jetty 无效导致修改流程拒绝继续执行
* 故障编号：urma_882
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_modify_jetty 在执行修改前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.50 urma_modify_jetty 校验 context 无效导致修改流程拒绝继续执行
* 故障编号：urma_883
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_modify_jetty 在执行修改前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.51 urma_flush_jetty 校验 Jetty 无效导致处理流程拒绝继续执行
* 故障编号：urma_884
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_flush_jetty 在执行处理前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.52 urma_advise_jetty 校验 目标 Jetty 无效导致处理流程拒绝继续执行
* 故障编号：urma_885
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_advise_jetty 在执行处理前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.53 urma_advise_jetty 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_886
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_advise_jetty 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.54 urma_advise_jetty 校验 Jetty 无效导致处理流程拒绝继续执行
* 故障编号：urma_887
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_advise_jetty 在执行处理前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.55 urma_unadvise_jetty 校验 目标 Jetty 无效导致处理流程拒绝继续执行
* 故障编号：urma_888
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unadvise_jetty 在执行处理前发现调用方传入的 目标 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.56 urma_unadvise_jetty 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_889
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unadvise_jetty 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.57 urma_unadvise_jetty 校验 Jetty 无效导致处理流程拒绝继续执行
* 故障编号：urma_890
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unadvise_jetty 在执行处理前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.58 urma_check_seg_cfg 校验 segment 无效导致校验流程拒绝继续执行
* 故障编号：urma_891
* 故障现象：
    * 关键日志：匹配 token_id must set when token_id_valid is true, or must NULL when token_id_valid is false
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_check_seg_cfg 在执行校验前发现调用方传入的 segment 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.59 urma_check_seg_cfg 执行校验 segment 失败导致当前资源状态无法推进
* 故障编号：urma_892
* 故障现象：
    * 关键日志：匹配 Local only access is not allowed to config with other accesses
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_check_seg_cfg 调用下层 provider、bond 组件或系统接口处理 segment 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.60 urma_check_seg_cfg 执行校验 segment 失败导致当前资源状态无法推进
* 故障编号：urma_893
* 故障现象：
    * 关键日志：匹配 Write access should be config with read access
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_check_seg_cfg 调用下层 provider、bond 组件或系统接口处理 segment 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.61 urma_check_seg_cfg 执行校验 segment 失败导致当前资源状态无法推进
* 故障编号：urma_894
* 故障现象：
    * 关键日志：匹配 Atomic access should be config with read and write access
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_check_seg_cfg 调用下层 provider、bond 组件或系统接口处理 segment 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
#### 9.62 urma_advise_jfr 校验 JFS 无效导致处理流程拒绝继续执行
* 故障编号：urma_895
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_advise_jfr 在执行处理前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.63 urma_advise_jfr 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_896
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_advise_jfr 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.64 urma_advise_jfr 校验 JFR 无效导致处理流程拒绝继续执行
* 故障编号：urma_897
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_advise_jfr 在执行处理前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.65 urma_unadvise_jfr 校验 JFS 无效导致处理流程拒绝继续执行
* 故障编号：urma_898
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unadvise_jfr 在执行处理前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.66 urma_unadvise_jfr 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_899
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unadvise_jfr 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.67 urma_unadvise_jfr 校验 JFR 无效导致处理流程拒绝继续执行
* 故障编号：urma_900
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_unadvise_jfr 在执行处理前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.68 urma_advise_jfr_async 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_901
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_advise_jfr_async 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.69 urma_advise_jfr_async 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_902
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_advise_jfr_async 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.70 urma_advise_jfr_async 校验 JFR 无效导致处理流程拒绝继续执行
* 故障编号：urma_903
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_advise_jfr_async 在执行处理前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.71 urma_user_ctl 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_904
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_user_ctl 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.72 urma_user_ctl 校验 context 无效导致处理流程拒绝继续执行
* 故障编号：urma_905
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_user_ctl 在执行处理前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.73 check_valid_sgl 校验 SGL 无效导致校验流程拒绝继续执行
* 故障编号：urma_906
* 故障现象：
    * 关键日志：匹配 sge is a null pointer
    * 日志路径：URMA_LOG_PATH
* 故障原因：check_valid_sgl 在执行校验前发现调用方传入的 SGL 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.74 check_valid_jfr_wr 校验 JFR 无效导致校验流程拒绝继续执行
* 故障编号：urma_907
* 故障现象：
    * 关键日志：匹配 There are invalid parameters
    * 日志路径：URMA_LOG_PATH
* 故障原因：check_valid_jfr_wr 在执行校验前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.75 urma_write 校验 JFS 无效导致处理流程拒绝继续执行
* 故障编号：urma_908
* 故障现象：
    * 关键日志：匹配 Invalid parameter
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_write 在执行处理前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.76 urma_str_to_eid 校验 EID 无效导致处理流程拒绝继续执行
* 故障编号：urma_909
* 故障现象：
    * 关键日志：匹配 Invalid argument
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_str_to_eid 在执行处理前发现调用方传入的 EID 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider 能力不一致，因此直接返回错误以避免继续访问非法资源。
* 解决办法：无
#### 9.77 urma_str_to_eid 执行处理 EID 失败导致当前资源状态无法推进
* 故障编号：urma_910
* 故障现象：
    * 关键日志：匹配 format error
    * 日志路径：URMA_LOG_PATH
* 故障原因：urma_str_to_eid 调用下层 provider、bond 组件或系统接口处理 EID 时返回失败，当前分支携带 ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。
* 解决办法：无
