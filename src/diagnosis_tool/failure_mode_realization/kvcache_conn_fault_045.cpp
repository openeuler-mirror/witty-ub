#include "kvcache_conn_fault_045.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault045> g_KvcacheConnFault045("kvcache_conn_fault_045");

KvcacheConnFault045::KvcacheConnFault045() noexcept
{
}

bool KvcacheConnFault045::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L790-L798
    // 来源: 10-customer-fault-scenarios.md L684-L687
    // 验证方法: ping -c 3 <node_ip>不通
    // 匹配逻辑: 运行`ping -c 3 <node_ip>`
    std::string output = kvcache_conn_utils::RunCommand(
        R"(ping -c 3 <node_ip> 2>/dev/null)");
    return output.find("unreachable") != std::string::npos;
}

std::string KvcacheConnFault045::GetName() const
{
    return "节点不可达";
}

std::string KvcacheConnFault045::GetRootCauseDesc() const
{
    return "主机/基础设施，联系机房/云平台";
}

RootCause KvcacheConnFault045::AnalyzeRootCause()
{
    return RootCause(true, "主机/基础设施，联系机房/云平台");
}

std::string KvcacheConnFault045::GetFixSuggDesc() const
{
    return "联系机房/云平台";
}

std::string KvcacheConnFault045::GetValidationMethodDesc() const
{
    return "ping -c 3 <node_ip>不通";
}

std::string KvcacheConnFault045::GetId() const
{
    return "kvcache_conn_fault_045";
}

} // namespace diag