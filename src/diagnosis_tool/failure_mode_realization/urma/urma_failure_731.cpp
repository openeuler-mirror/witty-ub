#include "urma_failure_731.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure731> g_urma("urma_731");

bool UrmaFailure731::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jetty_opt") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure731::GetName() const
{
    return "Jetty、缓冲区、len无效导致设置Jetty失败";
}

std::string UrmaFailure731::GetRootCauseDesc() const
{
    return "urma_set_jetty_opt用于设置Jetty，调用方传入的Jetty、缓冲区、len不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure731::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure731::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure731::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jetty_opt，Invalid parameter.。";
}

std::string UrmaFailure731::GetId() const
{
    return "urma_731";
}
} // namespace diag
