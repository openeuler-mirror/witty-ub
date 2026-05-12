#include "kvcache_conn_fault_011.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault011> g_KvcacheConnFault011("kvcache_conn_fault_011");

KvcacheConnFault011::KvcacheConnFault011() noexcept
{
}

bool KvcacheConnFault011::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L231-L244
    // 来源: 08-fault-triage-consolidated.md L199-L200
    // 来源: 10-customer-fault-scenarios.md L161-L162
    // 验证方法: INFO log含etcd is timeout或etcd is unavailable
    // 匹配逻辑: grep `etcd is timeout`或`etcd is unavailable` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E 'etcd is timeout|etcd is unavailable' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault011::GetName() const
{
    return "三方etcd（信号出现在DS日志中）";
}

std::string KvcacheConnFault011::GetRootCauseDesc() const
{
    return "etcd集群或到etcd的网络异常。主责三方etcd";
}

RootCause KvcacheConnFault011::AnalyzeRootCause()
{
    return RootCause(true, "etcd集群或到etcd的网络异常。主责三方etcd");
}

std::string KvcacheConnFault011::GetFixSuggDesc() const
{
    return "systemctl status etcd；etcdctl endpoint status；查到etcd的网络";
}

std::string KvcacheConnFault011::GetValidationMethodDesc() const
{
    return "INFO log含etcd is timeout或etcd is unavailable";
}

std::string KvcacheConnFault011::GetId() const
{
    return "kvcache_conn_fault_011";
}

} // namespace diag