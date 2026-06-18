#include "urma_failure_730.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure730> g_urma("urma_730");

bool UrmaFailure730::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_unadvise_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure730::GetName() const
{
    return "unadvise、Jetty无效导致unadviseunadvise、Jetty失败";
}

std::string UrmaFailure730::GetRootCauseDesc() const
{
    return "urma_unadvise_"
           "jetty用于unadviseunadvise、Jetty，调用方传入的unadvise、Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure730::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure730::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure730::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unadvise_jetty，Invalid parameter.。";
}

std::string UrmaFailure730::GetId() const
{
    return "urma_730";
}
} // namespace diag
