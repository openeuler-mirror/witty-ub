#include "urma_failure_086.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure086> g_urma("urma_086");

bool UrmaFailure086::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_unbind_jetty_async") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure086::GetName() const
{
    return "Jetty、URMA context、dev_fd、remote_jetty无效导致解绑Jetty失败";
}

std::string UrmaFailure086::GetRootCauseDesc() const
{
    return "urma_cmd_unbind_jetty_async用于解绑Jetty，调用方传入的Jetty、URMA "
           "context、dev_fd、remote_jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure086::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure086::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure086::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unbind_jetty_async，Invalid parameter。";
}

std::string UrmaFailure086::GetId() const
{
    return "urma_086";
}
} // namespace diag
