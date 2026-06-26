#include "kvcache_conn_fault_020_009.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault020_009> g_kvcacheconnfault("kvcache_conn_fault_020_009");

bool KvcacheConnFault020_009::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("zmq_event_handshake_failure_total") != std::string::npos);
}

std::string KvcacheConnFault020_009::GetName() const
{
    return "1001/1002 → yuanrong-datasystem进程内：TLS/认证配置（握手失败）。";
}

std::string KvcacheConnFault020_009::GetRootCauseDesc() const
{
    return "TLS/认证配置问题，属于yuanrong-datasystem进程内配置问题（08手册:L226）。";
}

RootCause KvcacheConnFault020_009::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_009::GetFixSuggDesc() const
{
    return "检查TLS证书配置、认证参数是否正确（08手册:L226）。";
}

std::string KvcacheConnFault020_009::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L226）：匹配zmq_event_handshake_failure_total增多。";
}

std::string KvcacheConnFault020_009::GetId() const
{
    return "kvcache_conn_fault_020_009";
}
} // namespace diag
