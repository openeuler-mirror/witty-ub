#include "kvcache_conn_fault_018.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault018> g_KvcacheConnFault018("kvcache_conn_fault_018");

KvcacheConnFault018::KvcacheConnFault018() noexcept
{
}

bool KvcacheConnFault018::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L346-L365
    // 来源: 08-fault-triage-consolidated.md L107-L108
    // 来源: 10-customer-fault-scenarios.md L173-L174
    // 验证方法: INFO log含[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]
    // 匹配逻辑: grep `\[UDS_CONNECT_FAILED\]`或`\[SHM_FD_TRANSFER_FAILED\]` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E '\[UDS_CONNECT_FAILED\]|\[SHM_FD_TRANSFER_FAILED\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault018::GetName() const
{
    return "UDS/SHM传fd失败";
}

std::string KvcacheConnFault018::GetRootCauseDesc() const
{
    return "同机UDS路径/权限/fd上限；SCM_RIGHTS发送失败多为fd耗尽或权限问题";
}

RootCause KvcacheConnFault018::AnalyzeRootCause()
{
    return RootCause(true, "同机UDS路径/权限/fd上限；SCM_RIGHTS发送失败多为fd耗尽或权限问题");
}

std::string KvcacheConnFault018::GetFixSuggDesc() const
{
    return "检查UDS路径/权限；调大ulimit -n";
}

std::string KvcacheConnFault018::GetValidationMethodDesc() const
{
    return "INFO log含[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]";
}

std::string KvcacheConnFault018::GetId() const
{
    return "kvcache_conn_fault_018";
}

} // namespace diag