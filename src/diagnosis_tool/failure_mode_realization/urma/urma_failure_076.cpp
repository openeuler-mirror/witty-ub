#include "urma_failure_076.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure076> g_urma("urma_076");

bool UrmaFailure076::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_bind_jetty") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure076::GetName() const
{
    return "Jetty、URMA context、dev_fd、目标Jetty无效导致绑定Jetty失败";
}

std::string UrmaFailure076::GetRootCauseDesc() const
{
    return "urma_cmd_bind_jetty用于绑定Jetty，调用方传入的Jetty、URMA "
           "context、dev_fd、目标Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure076::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure076::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure076::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_bind_jetty，Invalid parameter。";
}

std::string UrmaFailure076::GetId() const
{
    return "urma_076";
}
} // namespace diag
