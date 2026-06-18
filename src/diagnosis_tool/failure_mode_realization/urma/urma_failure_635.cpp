#include "urma_failure_635.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure635> g_urma("urma_635");

bool UrmaFailure635::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_eid_by_ip") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure635::GetName() const
{
    return "URMA context、net_addr、EID无效导致获取EID、IP失败";
}

std::string UrmaFailure635::GetRootCauseDesc() const
{
    return "urma_cmd_get_eid_by_ip用于获取EID、IP，调用方传入的URMA "
           "context、net_addr、EID不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure635::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure635::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure635::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_eid_by_ip，Invalid parameter.。";
}

std::string UrmaFailure635::GetId() const
{
    return "urma_635";
}
} // namespace diag
