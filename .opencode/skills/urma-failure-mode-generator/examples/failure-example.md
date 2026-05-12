# 模板说明：      
## 1 以故障树的形式组织故障模式，文档整体格式为：     
1. 一级故障            
1.1 二级故障       
1.1.1 三级故障     
1.1.2 三级故障
...   
1.2 二级故障       
1.2.1 三级故障
...

## 2 单个故障模式故障书写说明如下：
x.x... xxx故障模式名称
* 故障现象：
    * case1: 通过日志关键字识别故障现象，需给出
        * 日志路径：日志需要查看的日志文件路径
        * 关键字：在日志中用于识别故障现象的关键字，说明如下：        
            1、如果故障需要多行日志进行定位，给出每行日志待识别的关键字以及组合关系说明，例如需要满足关键字1，关键字2，关键字3才为此故障，或者匹配关键字1，关键字2，关键字3中一个即为此故障     
            2、可以给出具体日志示例（文本），用于辅助理解故障现象的判定标准。   
    * case 2：通过调用命令行并识别关键字识别故障现象，需给出
        * 执行命令行：需给出具体命令和参数。
        * 关键字：在命令行执行结果中需要识别的关键字，同case 1
    * case 3：故障现象需要经过多次日志和命令行调用进行组合逻辑判断，需说明详细步骤和步骤间的逻辑关系，每个步骤的说明规范见case 1和case 2,。
    * case 4：故障无具体现象，仅是逻辑上的故障分类，可不写，只列出故障名称
* 故障原因：
    * case 1：故障模式对应具体故障原因，需进行说明。
    * case 2：如故障还需向下级故障匹配，无法定位到根因可不写。
* 解决办法：
    * case 1：故障模式对应具体解决方法，需进行说明。
    * case 2：如故障还需向下级故障匹配，可不写。

# 示例
## brpc故障
#### 1 UBSocket设备信息填写错误，导致umq初始化失败
* 故障编号：urma_001
* 下级故障：[]
* 故障现象：
    * 关键日志：匹配get device failed
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：查看UBsocket环境变量填入的设备信息（设备名，设备eid）与当前环境urma_admin show查看的设备信息不一致
* 解决办法：查看urma_admin show和urma_admin show topo的urma设备，先用urma_perftest打流成功后，再填写设备信息（RPC_ADPT_DEV_NAME、RPC_ADPT_SRC_EID、RPC_ADPT_EID_IDX）。
#### 2 建链超时/RPC通信超时
* 故障编号：urma_002
* 下级故障：[]
* 故障现象：
    * 关键日志：匹配reached timeout
    * 日志路径：系统日志文件（URMA_LOG_PATH）
* 故障原因：bRPC设置的通信或者建链时间太小
* 解决办法：根据实际场景设置bRPC通信或者建链的时长。

## URMA故障
### 1 建链失败
* 故障编号：urma_001
* 下级故障：["urma_002"]
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。
#### 1.1 创建/查询TP失败
* 故障编号：urma_002
* 下级故障：["urma_003", "urma_004"]
* 故障现象：向下级匹配。
* 故障原因：向下级匹配。
* 解决方法：向下级匹配。
##### 1.1.1 get tp list 错误码 -2
* 故障编号：urma_003
* 下级故障：[]
* 故障现象：
    * 关键日志：[Fri Aug 29 19:45:58 2025] ubase 00003: UDMA: <udma_ctrlq_get_tpid_list:449> ctrlq send msg failed, ret = -2
    * 日志路径：URMA_LOG_PATH 或者dmesg
* 故障原因：primary_eid 不支持创建tp，如果指定创建tp就会出现-2错误。
* 解决办法：改成创建ctp即可解决
##### 1.1.1 get tp list 错误码 -11
* 故障编号：urma_004
* 下级故障：[]
* 故障现象：
    * 关键日志：Dec 5 10:24:47 localhost kernel: [861.969569] ubase 00007: UDMA: ctrlq send msg failed, ret = -11
    * 日志路径：URMA_LOG_PATH 或者dmesg
* 故障原因：lcne的环境没生效，未找到路由配置文件，导致路由下发失败
* 解决办法：
    ```
    cat /etc/sysman/env_variable
    mkdir -p /etc/sysman
    touch /etc/sysman/env_variable
    sudo chown lcne:verona /etc/sysman
    sudo chown lcne:verona /etc/sysman/env_variable
    echo "stub_slot_id=1" > /etc/sysman/env_variable
    echo "slotid=1" >> /etc/sysman/env_variable
    sed -i '/^scene=/d' /etc/sysman/env_variable && echo 'scene=1d8n2p' | sudo tee -a /etc/sysman/env_variable > /dev/null
    ```
