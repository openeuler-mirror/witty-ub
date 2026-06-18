#include "urma_failure_739.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure739> g_urma("urma_739");

bool UrmaFailure739::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_wait_notify") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure739::GetName() const
{
    return "Notifier、URMA context、notify无效导致waitWAIT、notify失败";
}

std::string UrmaFailure739::GetRootCauseDesc() const
{
    return "urma_wait_notify用于waitWAIT、notify，调用方传入的Notifier、URMA "
           "context、notify不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure739::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure739::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure739::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_wait_notify，Invalid parameter.。";
}

std::string UrmaFailure739::GetId() const
{
    return "urma_739";
}
} // namespace diag
