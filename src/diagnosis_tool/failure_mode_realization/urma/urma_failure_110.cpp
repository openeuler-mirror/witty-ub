#include "urma_failure_110.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure110> g_urma("urma_110");

bool UrmaFailure110::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_bind_jetty_ex") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure110::GetName() const
{
    return "Jetty、目标Jetty、配置参数无效导致绑定Jetty失败";
}

std::string UrmaFailure110::GetRootCauseDesc() const
{
    return "urma_bind_jetty_"
           "ex用于绑定Jetty，调用方传入的Jetty、目标Jetty、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure110::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure110::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure110::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_bind_jetty_ex，Invalid parameter.。";
}

std::string UrmaFailure110::GetId() const
{
    return "urma_110";
}
} // namespace diag
