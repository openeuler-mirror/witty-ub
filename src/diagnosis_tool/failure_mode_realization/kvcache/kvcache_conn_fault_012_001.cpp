#include "kvcache_conn_fault_012_001.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault012_001> g_kvcacheconnfault("kvcache_conn_fault_012_001");

bool KvcacheConnFault012_001::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("[RPC_RECV_TIMEOUT]") != std::string::npos ||
            message.find("[RPC_SERVICE_UNAVAILABLE]") != std::string::npos);
}

std::string KvcacheConnFault012_001::GetName() const
{
    return "对端处理慢/拒绝（RPC超时/服务不可用）。";
}

std::string KvcacheConnFault012_001::GetRootCauseDesc() const
{
    return "Worker对端处理慢或线程池打满导致RPC超时，属于yuanrong-datasystem进程内问题（08手册:L271）。";
}

RootCause KvcacheConnFault012_001::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault012_001::GetFixSuggDesc() const
{
    return "查Worker CPU使用率、锁争用情况；扩oc_rpc_thread_num线程数（08手册:L271）。";
}

std::string KvcacheConnFault012_001::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L271）：匹配[RPC_RECV_TIMEOUT]或[RPC_SERVICE_UNAVAILABLE]；"
           "配合resource.log中WAITING_TASK_NUM堆积。";
}

std::string KvcacheConnFault012_001::GetId() const
{
    return "kvcache_conn_fault_012_001";
}
} // namespace diag
