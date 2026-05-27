---
name: "kvcache-diagnosis-command-generalizer"
description: "基于witty-ub-diag-tool已有框架代码，增加日志路径的命令行参数，和对日志时间进行筛选的功能
---
# kvcache-diagnosis-command-generalizerll

## 目标：
基于witty-ub-diag-tool已有框架代码，witty-ub-diag-tool命令行增加参数来获取日志文件路径和开始结束时间，增加根据时间提取日志。

## 功能实现
阅读witty-ub-diag-tool的代码，仅新增以下功能，不要对代码中的业务内容进行修改，也不要优化代码，不要涉及其他skill的内容：

### 1 witty-ub-diag-tool 增加命令行参数
需要增加以下命令行参数：
1) 命令行参数 --ds-log-path 为必选参数，为所有日志所在目录，该参数不能为空，需要对目录是否存在进行校验，不存在则报错退出
2) 命令行参数 --ds-client-access-log-file 为必选参数，参数不能为空，参数有两种可能性：
  * 为具体的文件名，例如ds_client_access_1234.log，此时在--ds-log-path目录下所有目录搜索此文件名的日志文件，如不存在则报错退出
  * 为模糊需要匹配的文件名，支持通过\'*\'进行匹配，例如ds_client_access_\*.log，可以匹配ds_client_access_1234.log、ds_client_access_2345.log等，在--ds-log-path目录及所有下级目录下搜索符合的日志文件，如不存在则报错退出
3) 命令行参数 --ds-client-info-log-file 必选参数,参数不能为空，有两种可能性：
  * 为具体的文件名，例如ds_client_1234.INFO.log，此时在--ds-log-path目录下所有目录搜索此文件名的日志文件，如不存在则报错退出
  * 为模糊需要匹配的文件名，支持通过\'*\'进行匹配，例如ds_client_\*.INFO.log，在--ds-log-path目录及所有下级目录下搜索符合的日志文件，如不存在则报错退出
4) 命令行参数 --ds-worker-info-log-file 为必选参数，参数不能为空，有两种可能性：
  * 为具体的文件名，例如datasystem_worker.INFO.log，此时在--ds-log-path目录下所有目录下搜索此文件名的日志文件，如不存在则报错退出
  * 为模糊需要匹配的文件名，支持通过\'*\'进行匹配，例如datasystem_worker_\*.INFO.log，在--ds-log-path目录及所有下级目录下搜索符合的日志文件进行读取
5) 命令行参数 --resource-log-file 为必选参数，参数不能为空，Worker运行日志路径，有两种可能性：
  * 为具体的文件名，例如resource.log，此时在--ds-log-path目录下所有目录下搜索此文件名的日志文件，如不存在则报错退出
  * 为模糊需要匹配的文件名，支持通过\'*\'进行匹配，例如resource_\*.log，在--ds-log-path目录及所有下级目录下搜索符合的日志文件，如不存在则报错退出
6) 命令行参数 --start-time 为必选参数，故障识别的日志的开始时间,start-time格式为yyyy-mm-dd hh:mm:ss
7) 命令行参数 --end-time 为必选参数，故障识别的日志的结束时间,end-time格式为yyyy-mm-dd hh:mm:ss

### 2 根据时间窗提取日志
1.需要增加在故障定界代码执行之前，根据命令行参数输入的start time和end time作为时间窗，读取--ds-log-path、--ds-client-access-log-file、--ds-client-log-info-file、--ds_worker_log_info_file、--resource-log-file这些参数,在--ds-log-path指定的目录下搜索各个日志文件，读取日志文件在时间窗内的所有日志，保持原文件名分别写入到$WIIT_DIR/log目录下，例如--ds-client-access-log-file为ds_client_access_*.log，实际目录下存在ds_client_access_1111.log，ds_client_access_2222.log，那么统一需要写入ds_client_access_1111.log，ds_client_access_2222.log到$WIIT_DIR/log目录下，并设置：
* 环境变量$WITTY_UB_CLIENT_ACCESS_LOG环境变量为$WIIT_DIR/log/ds-client-access-log-file参数
* 环境变量$WITTY_UB_CLIENT_INFO_LOG环境变量为$WIIT_DIR/log/ds-client-log-info-file参数
* 环境变量$WITTY_UB_WORKER_INFO_LOG环境变量为$WIIT_DIR/log/ds-worker-log-info-file参数
* 环境变量$WITTY_UB_RESOURCES_LOG环境变量为$WIIT_DIR/log/ds-resources-log-file参数
* 环境变量$URMA_LOG_PATH环境变量为$WIIT_DIR/log/ds-worker-log-info-file参数
2.日志是按照时序打印的，当日志时间超过endtime时不需要再读取日志进行判断
3.日式格式为标准的 ISO 8601 格式，且带有微秒（6位小数），日志前缀为2026-05-13T15:27:26.442572 | I | access_recorder.cpp:219 | yxh-worker1-kvclient-1 | 10411:10411 | 3b73ff5c-5746-4cf5-b4bd-a894f05a4124 |

### 3 kvcache故障模式中查询的日志文件路径与命令行参数对应
修改kvcache故障模式的代码的命令行，替换写死的文件名为上面可配置的环境变量：
* 替换$WITTY_UB_FAULT_LOG/ds_client_access_*.log为$WITTY_UB_CLIENT_ACCESS_LOG
* 替换$WITTY_UB_FAULT_LOG/ds_client_*.INFO.log为$WITTY_UB_CLIENT_INFO_LOG
* 替换$WITTY_UB_FAULT_LOG/datasystem_worker.INFO.log为$WITTY_UB_WORKER_INFO_LOG
* 替换$WITTY_UB_FAULT_LOG/resource.log为$$WITTY_UB_RESOURCES_LOG

## 功能自测
在代码修改后，进行自测。编译witty-ub-diag-tool（只编译这个二进制，不考虑其他二进制编译报错），构造用例，对以下功能进行测试：
* --ds-log-path参数异常值：为空，为不存在的目录，不是目录，预期结果：报错退出
* --ds-client-access-log-file、--ds-client-info-log-file、--ds-worker-info-log-file、--resource-log-file日志文件的命令行参数传递异常值：为空、为不存在的文件、为目录路径不为文件路径，预期结果：报错退出
* 时间的命令行参数传递异常值：为空、不符合格式的时间，start time>end time，预期结果：报错退出
* 验证存在多层级目录时（>2级），--ds-client-access-log-file、--ds-client-info-log-file、--ds-worker-info-log-file、--resource-log-file为模糊匹配的情况下，即例如--ds-client-access-log-file为ds_client_access_*.log，/path/path1/1/ds_client_access_1234.log、/path/path2/2/ds_client_access_2345.log存在多个文件情况
* 验证时间筛选功能：在data/cmd-test/下创建测试文件，验证是否可以筛选指定时间窗内的日志，预期结果：时间窗内的日志被提取出来，并且环境变成设置成功
