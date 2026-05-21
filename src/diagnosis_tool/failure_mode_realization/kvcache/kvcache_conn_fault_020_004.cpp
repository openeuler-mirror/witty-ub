#include "kvcache_conn_fault_020_004.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_020_004 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L699, L702-703, L211, L338)
static AutoRegister<KvcacheConnFault020_004> g_kvcacheconnfault020_004("kvcache_conn_fault_020_004");

bool KvcacheConnFault020_004::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L699, L702-703, L211, L338
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E '\\[ZMQ_SEND_FAILURE_TOTAL\\]|\\[ZMQ_RECEIVE_FAILURE_TOTAL\\]' \"$WITTY_UB_FAULT_LOG\"/ds_client_*.INFO.log \"$WITTY_UB_FAULT_LOG\"/datasystem_worker.INFO.log 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault020_004::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L699, L702-703, L211, L338
    return "1001/1002 → OS侧ZMQ发送/接收失败";
}

std::string KvcacheConnFault020_004::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L699, L702-703, L211, L338
    return "ZMQ系统调用层硬失败，按errno对应OS问题。（来源：08手册:L338）";
}

RootCause KvcacheConnFault020_004::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L699, L702-703, L211, L338
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_004::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L699, L702-703, L211, L338
    return "按zmq_last_error_number对应的OS errno进行排查：检查端口/路由/防火墙/资源限制。（来源：08手册:L338）";
}

std::string KvcacheConnFault020_004::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L699, L702-703, L211, L338
    return "通过日志关键字识别（来源：08手册:L211, L338）：匹配[ZMQ_SEND_FAILURE_TOTAL]或[ZMQ_RECEIVE_FAILURE_TOTAL]。（来源：08手册:L211, L338）";
}

std::string KvcacheConnFault020_004::GetId() const
{
    return "kvcache_conn_fault_020_004";
}

} // namespace diag
