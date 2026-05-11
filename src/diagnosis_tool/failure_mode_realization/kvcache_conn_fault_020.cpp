#include "kvcache_conn_fault_020.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault020> g_KvcacheConnFault020("kvcache_conn_fault_020");

KvcacheConnFault020::KvcacheConnFault020() noexcept
{
}

bool KvcacheConnFault020::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L382-L394
    // 来源: 08-fault-triage-consolidated.md L113-L114
    // 来源: 10-customer-fault-scenarios.md L161-L166
    // 验证方法: INFO log含etcd is timeout或etcd is unavailable
    // 匹配逻辑: grep `etcd is timeout`或`etcd is unavailable` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E 'etcd is timeout|etcd is unavailable' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault020::GetName() const
{
    return "三方etcd层";
}

std::string KvcacheConnFault020::GetRootCauseDesc() const
{
    return "etcd集群或到etcd的网络异常";
}

RootCause KvcacheConnFault020::AnalyzeRootCause()
{
    return RootCause(true, "etcd集群或到etcd的网络异常");
}

std::string KvcacheConnFault020::GetFixSuggDesc() const
{
    return "systemctl status etcd；etcdctl endpoint status；查到etcd的网络";
}

std::string KvcacheConnFault020::GetValidationMethodDesc() const
{
    return "INFO log含etcd is timeout或etcd is unavailable";
}

std::string KvcacheConnFault020::GetId() const
{
    return "kvcache_conn_fault_020";
}

} // namespace diag