#include "urma_failure_085.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure085> g_urma("urma_085");

bool UrmaFailure085::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_bind_jetty_async") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure085::GetName() const
{
    return "Notifier、Jetty、URMA context、dev_fd无效导致绑定Jetty失败";
}

std::string UrmaFailure085::GetRootCauseDesc() const
{
    return "urma_cmd_bind_jetty_async用于绑定Jetty，调用方传入的Notifier、Jetty、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure085::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure085::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure085::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_bind_jetty_async，Invalid parameter。";
}

std::string UrmaFailure085::GetId() const
{
    return "urma_085";
}
} // namespace diag
