#include "urma_failure_696.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure696> g_urma("urma_696");

bool UrmaFailure696::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_unadvise_jetty") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure696::GetName() const
{
    return "unadvise、Jetty无效导致unadvise、Jetty失败";
}

std::string UrmaFailure696::GetRootCauseDesc() const
{
    return "urma_cmd_unadvise_"
           "jetty用于unadvise、Jetty，调用方传入的unadvise、Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure696::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure696::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure696::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unadvise_jetty，Invalid parameter。";
}

std::string UrmaFailure696::GetId() const
{
    return "urma_696";
}
} // namespace diag
