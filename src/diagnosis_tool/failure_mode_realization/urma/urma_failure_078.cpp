#include "urma_failure_078.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure078> g_urma("urma_078");

bool UrmaFailure078::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_unbind_jetty") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure078::GetName() const
{
    return "Jetty、URMA context、dev_fd、remote_jetty无效导致解绑Jetty失败";
}

std::string UrmaFailure078::GetRootCauseDesc() const
{
    return "urma_cmd_unbind_jetty用于解绑Jetty，调用方传入的Jetty、URMA "
           "context、dev_fd、remote_jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure078::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure078::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure078::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unbind_jetty，Invalid parameter。";
}

std::string UrmaFailure078::GetId() const
{
    return "urma_078";
}
} // namespace diag
