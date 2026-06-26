#include "kvcache_conn_fault_020_008.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault020_008> g_kvcacheconnfault("kvcache_conn_fault_020_008");

bool KvcacheConnFault020_008::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("[RPC_SERVICE_UNAVAILABLE]") != std::string::npos);
}

std::string KvcacheConnFault020_008::GetName() const
{
    return "1001/1002 → yuanrong-datasystem进程内：RPC服务不可用（对端主动拒绝）。";
}

std::string KvcacheConnFault020_008::GetRootCauseDesc() const
{
    return "对端Worker正在shutting down或状态异常，属于yuanrong-datasystem进程内问题（08手册:L225）。";
}

RootCause KvcacheConnFault020_008::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_008::GetFixSuggDesc() const
{
    return "检查对端Worker状态，确认是否在正常退出/扩缩容流程中；"
           "若非预期退出，检查Worker日志中的[HealthCheck]相关条目（08手册:L225, "
           "L274）。";
}

std::string KvcacheConnFault020_008::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L225）：匹配[RPC_SERVICE_UNAVAILABLE]。";
}

std::string KvcacheConnFault020_008::GetId() const
{
    return "kvcache_conn_fault_020_008";
}
} // namespace diag
