#include "urma_failure_119.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure119> g_urma("urma_119");

bool UrmaFailure119::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_bind_jetty_async") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure119::GetName() const
{
    return "Notifier、Jetty、目标Jetty无效导致绑定Jetty失败";
}

std::string UrmaFailure119::GetRootCauseDesc() const
{
    return "urma_bind_jetty_"
           "async用于绑定Jetty，调用方传入的Notifier、Jetty、目标Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure119::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure119::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure119::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_bind_jetty_async，Invalid parameter.。";
}

std::string UrmaFailure119::GetId() const
{
    return "urma_119";
}
} // namespace diag
