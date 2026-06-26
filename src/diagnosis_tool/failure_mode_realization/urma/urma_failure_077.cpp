#include "urma_failure_077.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure077> g_urma("urma_077");

bool UrmaFailure077::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_bind_jetty_ex") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure077::GetName() const
{
    return "Jetty、URMA context、dev_fd、目标Jetty无效导致绑定Jetty失败";
}

std::string UrmaFailure077::GetRootCauseDesc() const
{
    return "urma_cmd_bind_jetty_ex用于绑定Jetty，调用方传入的Jetty、URMA "
           "context、dev_fd、目标Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure077::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure077::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure077::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_bind_jetty_ex，Invalid parameter.。";
}

std::string UrmaFailure077::GetId() const
{
    return "urma_077";
}
} // namespace diag
