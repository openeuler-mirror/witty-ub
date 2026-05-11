#include "kvcache_conn_fault_044.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault044> g_KvcacheConnFault044("kvcache_conn_fault_044");

KvcacheConnFault044::KvcacheConnFault044() noexcept
{
}

bool KvcacheConnFault044::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L777-L788
    // 来源: 10-customer-fault-scenarios.md L676-L677
    // 验证方法: INFO log含大量K_CLIENT_WORKER_DISCONNECT(23)/K_RPC_UNAVAILABLE(1002)/Cannot receive heartbeat from worker聚集在某节点
    // 匹配逻辑: grep `Cannot receive heartbeat from worker`或`K_CLIENT_WORKER_DISCONNECT` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E 'Cannot receive heartbeat from worker|K_CLIENT_WORKER_DISCONNECT' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault044::GetName() const
{
    return "机器/节点级故障";
}

std::string KvcacheConnFault044::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause KvcacheConnFault044::AnalyzeRootCause()
{
    return RootCause(false, "向下级匹配。");
}

std::string KvcacheConnFault044::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string KvcacheConnFault044::GetValidationMethodDesc() const
{
    return "INFO log含大量K_CLIENT_WORKER_DISCONNECT(23)/K_RPC_UNAVAILABLE(1002)/Cannot receive heartbeat from worker聚集在某节点";
}

std::string KvcacheConnFault044::GetId() const
{
    return "kvcache_conn_fault_044";
}

} // namespace diag