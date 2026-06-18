#include "urma_failure_701.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure701> g_urma("urma_701");

bool UrmaFailure701::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_active_jetty") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure701::GetName() const
{
    return "Jetty、URMA context、dev_fd无效导致激活Jetty失败";
}

std::string UrmaFailure701::GetRootCauseDesc() const
{
    return "urma_cmd_active_jetty用于激活Jetty，调用方传入的Jetty、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure701::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure701::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure701::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_active_jetty，Invalid parameter。";
}

std::string UrmaFailure701::GetId() const
{
    return "urma_701";
}
} // namespace diag
