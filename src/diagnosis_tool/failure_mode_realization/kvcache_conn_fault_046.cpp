#include "kvcache_conn_fault_046.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault046> g_KvcacheConnFault046("kvcache_conn_fault_046");

KvcacheConnFault046::KvcacheConnFault046() noexcept
{
}

bool KvcacheConnFault046::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L800-L808
    // 来源: 10-customer-fault-scenarios.md L686-L687
    // 验证方法: kubectl describe node含taints/conditions异常
    // 匹配逻辑: 运行`kubectl describe node <n>`
    std::string output = kvcache_conn_utils::RunCommand(
        R"(kubectl describe node <n> 2>/dev/null)");
    return output.find("NotReady") != std::string::npos;
}

std::string KvcacheConnFault046::GetName() const
{
    return "节点NotReady（k8s）";
}

std::string KvcacheConnFault046::GetRootCauseDesc() const
{
    return "编排/主机问题";
}

RootCause KvcacheConnFault046::AnalyzeRootCause()
{
    return RootCause(true, "编排/主机问题");
}

std::string KvcacheConnFault046::GetFixSuggDesc() const
{
    return "编排/主机运维排查";
}

std::string KvcacheConnFault046::GetValidationMethodDesc() const
{
    return "kubectl describe node含taints/conditions异常";
}

std::string KvcacheConnFault046::GetId() const
{
    return "kvcache_conn_fault_046";
}

} // namespace diag