#include "kvcache_conn_fault_039.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault039> g_KvcacheConnFault039("kvcache_conn_fault_039");

KvcacheConnFault039::KvcacheConnFault039() noexcept
{
}

bool KvcacheConnFault039::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L722-L730
    // 来源: 10-customer-fault-scenarios.md L513-L514
    // 验证方法: pgrep -af datasystem_worker无结果
    // 匹配逻辑: 运行`pgrep -af datasystem_worker`
    std::string output = kvcache_conn_utils::RunCommand(
        R"(pgrep -af datasystem_worker 2>/dev/null)");
    return output.empty();
}

std::string KvcacheConnFault039::GetName() const
{
    return "Worker进程不存在";
}

std::string KvcacheConnFault039::GetRootCauseDesc() const
{
    return "DataSystem/编排问题，Worker未拉起";
}

RootCause KvcacheConnFault039::AnalyzeRootCause()
{
    return RootCause(true, "DataSystem/编排问题，Worker未拉起");
}

std::string KvcacheConnFault039::GetFixSuggDesc() const
{
    return "联系华为DS支持或编排侧拉起（systemd/k8s查重启原因：kubectl describe / journalctl -u ...）";
}

std::string KvcacheConnFault039::GetValidationMethodDesc() const
{
    return "pgrep -af datasystem_worker无结果";
}

std::string KvcacheConnFault039::GetId() const
{
    return "kvcache_conn_fault_039";
}

} // namespace diag