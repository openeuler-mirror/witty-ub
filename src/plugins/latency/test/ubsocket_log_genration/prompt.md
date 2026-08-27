我需要你生成1个ubsocket故障日志数据集，下面我会描述数据集的生成方法。
ubsocket源码路径：/Users/zhaoyujin/Desktop/brpc_urma_code/ubs-comm/src/ubsocket/csrc，umq源码路径：/Users/zhaoyujin/Desktop/brpc_urma_code/ubs-comm/src/hcom/umq/src，urma源码路径：/Users/zhaoyujin/Desktop/brpc_urma_code/umdk-26.06.0/src/urma/lib/urma。
你需要模拟调用ubsocket的公开API时可能出现的部分错误日志。生成日志的路径为/Users/zhaoyujin/Desktop/witty-ubtest/ubsocket_log_genration/log_1/logs。
要求1：有ubsocket内部的，有ubsocket->umq的，有ubsocket->umq->urma4brpc的。已经生成了这三个组件的各个错误日志点的信息：/Users/zhaoyujin/Desktop/witty-ub/data/ubsocket/ubsocket_failure_mode.json、/Users/zhaoyujin/Desktop/witty-ub/data/ubsocket/ubsocket_failure_mode.json、/Users/zhaoyujin/Desktop/witty-ub/data/urma/urma_failure_mode_for_brpc.json和它们的层级关系：/Users/zhaoyujin/Desktop/witty-ub/data/failure_mode_tree.json（ubsocket、umq和urma4brpc部分）。
要求2：一个thread id对应多次调用ubsocket API的请求。这些请求可能有正确的，可能有错误的。请参照要求1生成正确和错误请求的日志。单个请求的日志前后保持顺序，多个请求的日志可能会互相交错。
要求3：日志格式为“[time][pod_name][pod_ip][component][filename:function_name:line_number][thread_id(optional)][trace_id(optional)] message”，其中time的格式是"YYYYMMDD HH:MM:SS.6位微秒"。对于ubsocket和umq的日志，component为UBSOCKET和UMQ，message就是日志宏输出的文本；对于urma日志，component为UMQ，filename、function_name、line_number为umq调用urma api的地方，message格式为[URMA][thread_id=xxx][trace_id(optional)][filename:function_name:line_number]message，这里的filename:function_name:line_number是urma的函数产生错误日志的位置，message是urma日志宏输出的文本（相当于一条完整的urma日志充当了brpc日志的message）。上述所有的可选项，不存在时内容为“-”。
要求4：所有日志的起始时间在2026-08-01 00:00:00至今范围内，总体跨度在15-30分钟。所有日志的量在100行左右。日志包含多个文件，每个文件下面是所有同一pod ip的日志，文件名是pod ip。
你还需要生成故障的ground truth，明确指出生成的日志中的相应故障。生成的文件路径为/Users/zhaoyujin/Desktop/witty-ubtest/ubsocket_log_genration/log_1/ground_truth。生成两个文件：
1.aggregate_event.json：包含各个pod的聚合故障信息，为下面的字典格式：
{
    "[pod_ip]": {
        "total": [所有故障日志的总数],
        "[api_1（故障的公共API）]": [该故障API的故障日志总数],
        "[api_2（故障的公共API）]": [该故障API的故障日志总数],
        ...
    }
    ...
}
这里，公共API是ubsocket、umq和urma4brpc的failure mode中，没有上级节点或者上级节点属于上级组建的故障模式对应的函数，具体可以参考前后端实现。
2.anomaly_threads.json：包含异常thread的列表，为一个字典，key为thread_id，value为各个故障模式链及其数量，为下面的字典格式：
{
    "[thread_id]": {
        [
            {
                "failure_mode_chain": "[failure_mode_id1, failure_mode_id2, ...]",
                "count": [该故障模式链的日志数量]
            },
            {
                "failure_mode_chain": "[failure_mode_id1, failure_mode_id2, ...]",
                "count": [该故障模式链的日志数量]
            },
            ...
        ]
    }
    ...
}
其中，failure_mode_chain时failure_mode_id的列表，从上游模式到下游模式依次排列。