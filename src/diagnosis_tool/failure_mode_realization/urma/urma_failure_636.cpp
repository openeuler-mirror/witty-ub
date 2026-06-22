#include "urma_failure_636.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure636> g_urma("urma_636");

bool UrmaFailure636::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_ip_by_eid") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure636::GetName() const
{
    return "URMA context、EID、net_addr无效导致获取IP、EID失败";
}

std::string UrmaFailure636::GetRootCauseDesc() const
{
    return "urma_cmd_get_ip_by_eid用于获取IP、EID，调用方传入的URMA "
           "context、EID、net_addr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure636::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure636::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure636::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_ip_by_eid，Invalid parameter.。";
}

std::string UrmaFailure636::GetId() const
{
    return "urma_636";
}
} // namespace diag
