#include "kvcache_conn_fault_012.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault012> g_KvcacheConnFault012("kvcache_conn_fault_012");

KvcacheConnFault012::KvcacheConnFault012() noexcept
{
}

bool KvcacheConnFault012::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L246-L258
    // 来源: 08-fault-triage-consolidated.md L202-L204
    // 来源: 10-customer-fault-scenarios.md L621-L632
    // 验证方法: INFO log含Cannot receive heartbeat from worker或HealthCheck Worker is exiting now或meta_is_moving
    // 匹配逻辑: grep `Cannot receive heartbeat from worker`或`Worker is exiting now`或`meta_is_moving` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E 'Cannot receive heartbeat from worker|Worker is exiting now|meta_is_moving' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault012::GetName() const
{
    return "心跳/生命周期/扩缩容";
}

std::string KvcacheConnFault012::GetRootCauseDesc() const
{
    return "心跳断→Worker被STOP；退出由编排拉起；扩缩容中SDK自重试";
}

RootCause KvcacheConnFault012::AnalyzeRootCause()
{
    return RootCause(true, "心跳断→Worker被STOP；退出由编排拉起；扩缩容中SDK自重试");
}

std::string KvcacheConnFault012::GetFixSuggDesc() const
{
    return "心跳断→kill -CONT <pid>；退出由编排拉起；扩缩容SDK自重试";
}

std::string KvcacheConnFault012::GetValidationMethodDesc() const
{
    return "INFO log含Cannot receive heartbeat from worker或HealthCheck Worker is exiting now或meta_is_moving";
}

std::string KvcacheConnFault012::GetId() const
{
    return "kvcache_conn_fault_012";
}

} // namespace diag