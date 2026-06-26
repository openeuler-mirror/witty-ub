#include "urma_failure_693.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure693> g_urma("urma_693");

bool UrmaFailure693::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_advise_jetty") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure693::GetName() const
{
    return "Jetty、URMA context、dev_fd、目标Jetty无效导致advise、Jetty失败";
}

std::string UrmaFailure693::GetRootCauseDesc() const
{
    return "urma_cmd_advise_jetty用于advise、Jetty，调用方传入的Jetty、URMA "
           "context、dev_fd、目标Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure693::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure693::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure693::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_advise_jetty，Invalid parameter。";
}

std::string UrmaFailure693::GetId() const
{
    return "urma_693";
}
} // namespace diag
