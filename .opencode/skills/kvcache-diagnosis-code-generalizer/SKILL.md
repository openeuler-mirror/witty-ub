---
name: "kvcache-diagnosis-code-generalizer"
description: "基于witty-ub-diag-tool已有框架代码，增加日志路径的命令行参数，和对日志时间进行筛选的功能
---
# kvcache-diagnosis-code-generalizer

## 目标：
基于witty-ub-diag-tool已有框架代码，witty-ub-diag-tool命令行增加参数来获取日志文件路径和开始结束时间，增加根据时间提取日志。

## 功能实现
阅读witty-ub-diag-tool的代码，仅新增以下功能，不要对代码中的业务内容进行修改，也不要优化代码，不要涉及其他skill的内容：
### 1 witty-ub-diag-tool 增加命令行参数
需要增加以下命令行参数，参数需要校验，例如path路径是否存在，时间参数是否符合格式，start time是否小于end time等
1) 命令行参数 --ds-client-access-log-path 为必选参数,为SDK接口访问日志路径，一般为/path/client/ds_client_access_<pid>.log
2) 命令行参数 --ds-client-access-log-path 为必选参数,为SDK运行日志路径，一般为/path/client/ds_client_<pid>.INFO.log
3) 命令行参数 --ds_worker_log_info_path 为必选参数，Worker运行日志路径，一般为/path/yr_datasystem/logs/{log_filename}.INFO.log
4) 命令行参数 --resource-log-path 为必选参数，Worker资源使用日志路径，一般为/path/yr_datasystem/logs/resource.log的形式
5) 命令行参数 --start-time 为必选参数，故障识别的日志的开始时间,start-time格式为yyyy-mm-dd hh:mm:ss
6) 命令行参数 --end-time 为必选参数，故障识别的日志的结束时间,end-time格式为yyyy-mm-dd hh:mm:ss

### 2 根据时间窗提取日志
1.需要增加在故障定界代码执行之前，根据命令行参数输入的start time和end time作为时间窗，读取以上--ds-client-access-log-path、--ds-client-access-log-path、--ds_worker_log_info_path、--resource.log参数输入的日志文件,获取各个日志文件中时间窗内的所有日志，保持原文件名写入到/var/witty-ub/log/date（命令行执行的时间）目录下，并设置环境变量$WITTY-UB-FAULT-LOG环境变量为此目录
2.日志是按照时序打印的，当日志时间超过endtime时不需要再读取日志进行判断
3.日式格式为标准的 ISO 8601 格式，且带有微秒（6位小数），日志前缀为2026-05-13T15:27:26.442572 | I | access_recorder.cpp:219 | yxh-worker1-kvclient-1 | 10411:10411 | 3b73ff5c-5746-4cf5-b4bd-a894f05a4124 |

## 功能自测
### 1 witty-ub-diag-tool 增加命令行参数
