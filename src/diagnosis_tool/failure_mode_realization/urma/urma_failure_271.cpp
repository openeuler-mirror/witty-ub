#include "urma_failure_271.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure271> g_urma("urma_271");

bool UrmaFailure271::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_ip_by_eid") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure271::GetName() const
{
    return "provider未提供get_eid_by_ip操作实现无效导致获取IP、EID失败";
}

std::string UrmaFailure271::GetRootCauseDesc() const
{
    return "urma_get_ip_by_eid用于获取IP、EID，调用方传入的provider未提供get_eid_by_"
           "ip操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure271::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure271::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure271::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_ip_by_eid，Invalid parameter.。";
}

std::string UrmaFailure271::GetId() const
{
    return "urma_271";
}
} // namespace diag
