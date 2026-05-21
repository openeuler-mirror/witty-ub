#include "kvcache_conn_fault_020_003.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_020_003 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L680, L683-684, L210, L335)
static AutoRegister<KvcacheConnFault020_003> g_kvcacheconnfault020_003("kvcache_conn_fault_020_003");

bool KvcacheConnFault020_003::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L680, L683-684, L210, L335
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E '\\[UDS_CONNECT_FAILED\\]|\\[SHM_FD_TRANSFER_FAILED\\]' \"$WITTY_UB_FAULT_LOG\"/ds_client_*.INFO.log \"$WITTY_UB_FAULT_LOG\"/datasystem_worker.INFO.log 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault020_003::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L680, L683-684, L210, L335
    return "1001/1002 → OS侧UDS连接失败/SHM fd传输失败";
}

std::string KvcacheConnFault020_003::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L680, L683-684, L210, L335
    return "同机UDS路径不存在/权限不足/fd耗尽，SCM_RIGHTS发送失败多为fd耗尽或权限，属于OS层。（来源：08手册:L210, L335）";
}

RootCause KvcacheConnFault020_003::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L680, L683-684, L210, L335
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_003::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L680, L683-684, L210, L335
    return "检查UDS路径和权限；检查fd上限（ls /proc/<pid>/fd | wc -l vs ulimit -n）。（来源：08手册:L335）";
}

std::string KvcacheConnFault020_003::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L680, L683-684, L210, L335
    return "通过日志关键字识别（来源：08手册:L210, L335）：匹配[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]。（来源：08手册:L210, L335）";
}

std::string KvcacheConnFault020_003::GetId() const
{
    return "kvcache_conn_fault_020_003";
}

} // namespace diag
