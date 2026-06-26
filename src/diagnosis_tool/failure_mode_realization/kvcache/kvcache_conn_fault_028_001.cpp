#include "kvcache_conn_fault_028_001.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault028_001> g_kvcacheconnfault("kvcache_conn_fault_028_001");

bool KvcacheConnFault028_001::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("[URMA_NEED_CONNECT]") != std::string::npos);
}

std::string KvcacheConnFault028_001::GetName() const
{
    return "URMA_NEED_CONNECT(对端Worker重启或UB链路不稳）。";
}

std::string KvcacheConnFault028_001::GetRootCauseDesc() const
{
    return "case 1:对端Worker重启导致URMA连接失效，属于预期行为，"
           "等待SDK自重连稳定（08手册:L297）; case 2: UB链路不稳，"
           "需区分是硬件/驱动问题还是端口/交换机抖动（08手册:L298）。";
}

RootCause KvcacheConnFault028_001::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_001::GetFixSuggDesc() const
{
    return "case 1: 确认对端Worker确实重启后，等待SDK自重连稳定；"
           "若重启由编排触发则属正常（08手册:L297）;case2: 检查UB端口状态和交换机；"
           "若伴POLL_ERROR/RECREATE_JFS则需联系URMA/UB运维（08手册:L298）。";
}

std::string KvcacheConnFault028_001::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L297）：匹配[URMA_NEED_CONNECT]。";
}

std::string KvcacheConnFault028_001::GetId() const
{
    return "kvcache_conn_fault_028_001";
}
} // namespace diag
