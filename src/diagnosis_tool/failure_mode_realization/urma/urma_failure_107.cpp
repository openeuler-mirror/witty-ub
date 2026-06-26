#include "urma_failure_107.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure107> g_urma("urma_107");

bool UrmaFailure107::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_bind_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure107::GetName() const
{
    return "Jetty、目标Jetty无效导致绑定Jetty失败";
}

std::string UrmaFailure107::GetRootCauseDesc() const
{
    return "urma_bind_jetty用于绑定Jetty，调用方传入的Jetty、目标Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure107::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure107::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure107::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_bind_jetty，Invalid parameter.。";
}

std::string UrmaFailure107::GetId() const
{
    return "urma_107";
}
} // namespace diag
