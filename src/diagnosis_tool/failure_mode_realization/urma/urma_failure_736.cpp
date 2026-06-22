#include "urma_failure_736.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure736> g_urma("urma_736");

bool UrmaFailure736::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure736::GetName() const
{
    return "Jetty无效导致激活Jetty失败";
}

std::string UrmaFailure736::GetRootCauseDesc() const
{
    return "urma_active_jetty用于激活Jetty，调用方传入的Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure736::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure736::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure736::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jetty，Invalid parameter.。";
}

std::string UrmaFailure736::GetId() const
{
    return "urma_736";
}
} // namespace diag
