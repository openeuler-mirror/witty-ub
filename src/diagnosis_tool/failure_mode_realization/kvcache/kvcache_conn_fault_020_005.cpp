#include "kvcache_conn_fault_020_005.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_020_005 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L731, L734-735, L217)
static AutoRegister<KvcacheConnFault020_005> g_kvcacheconnfault020_005("kvcache_conn_fault_020_005");

bool KvcacheConnFault020_005::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L731, L734-735, L217
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && grep -E 'etcd is (timeout|unavailable)' $WITTY_UB_WORKER_INFO_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    grepOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(grepOutput);
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault020_005::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L731, L734-735, L217
    return "1001/1002 → 三方etcd（etcd超时/不可用）";
}

std::string KvcacheConnFault020_005::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L731, L734-735, L217
    return "etcd集群或到etcd的网络问题，属于三方etcd责任。（来源：08手册:L217）";
}

RootCause KvcacheConnFault020_005::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L731, L734-735, L217
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_005::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L731, L734-735, L217
    return "systemctl status etcd；etcdctl endpoint status；排查到etcd的网络。（来源：08手册:L273）";
}

std::string KvcacheConnFault020_005::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L731, L734-735, L217
    return "通过日志关键字识别（来源：08手册:L217）：匹配etcd is timeout或etcd is unavailable，常同屏出现1002/25错误码。（来源：08手册:L217）";
}

std::string KvcacheConnFault020_005::GetId() const
{
    return "kvcache_conn_fault_020_005";
}

} // namespace diag
