#include "kvcache_conn_fault_012_003.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_012_003 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L567, L569-571, L273, L632-633)
static AutoRegister<KvcacheConnFault012_003> g_kvcacheconnfault012_003("kvcache_conn_fault_012_003");

bool KvcacheConnFault012_003::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L567, L569-571, L273, L632-633
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E 'etcd is (timeout|unavailable)' \"$WITTY_UB_FAULT_LOG\"/datasystem_worker.INFO.log 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault012_003::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L567, L569-571, L273, L632-633
    return "三方etcd（Master/Worker日志中出现etcd超时）";
}

std::string KvcacheConnFault012_003::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L567, L569-571, L273, L632-633
    return "主责写三方etcd。（来源：08手册:L273）";
}

RootCause KvcacheConnFault012_003::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L567, L569-571, L273, L632-633
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault012_003::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L567, L569-571, L273, L632-633
    return "systemctl status etcd；etcdctl endpoint status；排查到etcd的网络。（来源：08手册:L273）";
}

std::string KvcacheConnFault012_003::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L567, L569-571, L273, L632-633
    return "通过日志关键字识别（来源：08手册:L273）：匹配etcd is timeout或etcd is unavailable；配合resource.log中ETCD_QUEUE堆积。（来源：08手册:L273, L632-633）";
}

std::string KvcacheConnFault012_003::GetId() const
{
    return "kvcache_conn_fault_012_003";
}

} // namespace diag
