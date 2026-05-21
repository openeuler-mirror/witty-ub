#include "kvcache_conn_fault_042.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault042> g_KvcacheConnFault042("kvcache_conn_fault_042");

KvcacheConnFault042::KvcacheConnFault042() noexcept
{
}

bool KvcacheConnFault042::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L760-L770
    // 来源: 10-customer-fault-scenarios.md L539-L540
    // 验证方法: INFO log含[UDS_CONNECT_FAILED]
    // 匹配逻辑: grep `\[UDS_CONNECT_FAILED\]` 输出非空
    std::string grepOutput = kvcache_conn_utils::RunCommand(
        R"(grep -E '\[UDS_CONNECT_FAILED\]' $LOG/datasystem_worker.INFO.log $LOG/ds_client_*.INFO.log 2>/dev/null)");
    return !grepOutput.empty();
}

std::string KvcacheConnFault042::GetName() const
{
    return "UDS路径/权限问题";
}

std::string KvcacheConnFault042::GetRootCauseDesc() const
{
    return "主机，同机UDS路径/权限/tenant_id不一致";
}

RootCause KvcacheConnFault042::AnalyzeRootCause()
{
    return RootCause(true, "主机，同机UDS路径/权限/tenant_id不一致");
}

std::string KvcacheConnFault042::GetFixSuggDesc() const
{
    return "ls -la <uds_path>检查路径与权限；改权限/按部署文档挂载";
}

std::string KvcacheConnFault042::GetValidationMethodDesc() const
{
    return "INFO log含[UDS_CONNECT_FAILED]";
}

std::string KvcacheConnFault042::GetId() const
{
    return "kvcache_conn_fault_042";
}

} // namespace diag