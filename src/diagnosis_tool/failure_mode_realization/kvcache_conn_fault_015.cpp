#include "kvcache_conn_fault_015.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault015> g_KvcacheConnFault015("kvcache_conn_fault_015");

KvcacheConnFault015::KvcacheConnFault015() noexcept
{
}

bool KvcacheConnFault015::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L302-L316
    // 来源: 08-fault-triage-consolidated.md L103-L110
    // 来源: 10-customer-fault-scenarios.md L169-L178
    // 验证方法: INFO log含[TCP_CONNECT_FAILED]或[TCP_CONNECT_RESET]或[TCP_NETWORK_UNREACHABLE]或[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]或[ZMQ_SEND_FAILURE_TOTAL]或[ZMQ_RECEIVE_FAILURE_TOTAL]
    // 匹配逻辑: grep `\[(TCP`或`UDS`或`ZMQ`或`SHM_FD)_` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"cmd(grep -E '\[(TCP|UDS|ZMQ|SHM_FD)_' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)cmd");
    return !grepOutput.empty();
}

std::string KvcacheConnFault015::GetName() const
{
    return "OS层（TCP/UDS/ZMQ系统调用层）";
}

std::string KvcacheConnFault015::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause KvcacheConnFault015::AnalyzeRootCause()
{
    return RootCause(false, "向下级匹配。");
}

std::string KvcacheConnFault015::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string KvcacheConnFault015::GetValidationMethodDesc() const
{
    return "INFO log含[TCP_CONNECT_FAILED]或[TCP_CONNECT_RESET]或[TCP_NETWORK_UNREACHABLE]或[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]或[ZMQ_SEND_FAILURE_TOTAL]或[ZMQ_RECEIVE_FAILURE_TOTAL]";
}

std::string KvcacheConnFault015::GetId() const
{
    return "kvcache_conn_fault_015";
}

} // namespace diag