---
name: "kvcache-diagnosis-code-generalizer"
description: "基于witty-ub-diag-tool已有框架代码，增加日志路径的命令行参数，为kvcache故障定界能力增加trace id的匹配规则，和结果文件输出"
---
# kvcache-diagnosis-code-generalizer

## 目标：
基于witty-ub-diag-tool已有框架代码，和skill kvcache-diagnosis-conn-fault-code-generalizer生成的故障模式的代码，witty-ub-diag-tool命令行增加参数来获取日志文件路径和开始结束时间，增加根据时间提取日志，修改kvcache的故障定界增加日志采集和结果文件输出。

## 实现功能
需要新增的功能如下: 先输出设计文档，然后修改代码
### 1 witty-ub-diag-tool 增加命令行参数
需要增加以下命令行参数，参数需要校验，例如path路径是否存在，时间参数是否符合格式，start time是否小于end time等
1) 命令行参数 --ds-client-access-log-path 为必选参数,为SDK接口访问日志路径，一般为/path/client/ds_client_access_<pid>.log
2) 命令行参数 --ds-client-access-log-path 为必选参数,为SDK运行日志路径，一般为/path/client/ds_client_<pid>.INFO.log
3) 命令行参数 --ds_worker_log_info_path 为必选参数，Worker运行日志路径，一般为/path/yr_datasystem/logs/{log_filename}.INFO.log
4) 命令行参数 --resource-log-path 为必选参数，Worker资源使用日志路径，一般为/path/yr_datasystem/logs/resource.log的形式
5) 命令行参数 --start-time 为必选参数，故障识别的日志的开始时间,start-time格式为yyyy-mm-dd hh:mm:ss
6) 命令行参数 --end-time 为必选参数，故障识别的日志的结束时间,end-time格式为yyyy-mm-dd hh:mm:ss

### 2 根据时间窗提取日志
需要增加在故障定界代码执行之前，根据命令行参数输入的start time和end time作为时间窗，读取以上--ds-client-access-log-path、--ds-client-access-log-path、--ds_worker_log_info_path、--resource.log参数输入的日志文件,获取各个日志文件中时间窗内的所有日志，保持原文件名写入到/var/witty-ub/log/date（命令行执行的时间）目录下，并设置环境变量$WITTY-UB-FAULT-LOG环境变量为此目录

### 3 kvcache故障定界
基于现在witty-ub-diag-tool框架，增加kvcache故障定界接入到定界框架中：
1）阅读src/witty_ub_diag_tool_main.cpp和src/diagnosis_tool源码，理解代码逻辑和failure_mode、failure_controller等类的成员变量的含义
2）修改现有代码，删除kvcache中故障判断与trace id关联的内容（删除因为这个功能添加的函数、变量等内容）
3）增加在匹配过程中匹配到的故障行，以及相关故障日志信息，尽量复用代码中现有的内容，例如可以保存日志信息到FailureLogInfo中
4）参考urma定界代码逻辑，和可视化代码，调用可视化的接口函数，让kvcache与urma一样生成json文件和html文件到/var/witty-ub-witty-ub-diag目录下