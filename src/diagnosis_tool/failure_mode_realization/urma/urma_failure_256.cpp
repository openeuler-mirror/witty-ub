#include "urma_failure_256.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure256> g_urma("urma_256");

bool UrmaFailure256::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_jetty_opt") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure256::GetName() const
{
    return "Jetty无效导致获取Jetty失败";
}

std::string UrmaFailure256::GetRootCauseDesc() const
{
    return "urma_get_jetty_opt用于获取Jetty，调用方传入的Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure256::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure256::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure256::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jetty_opt，Invalid parameter.。";
}

std::string UrmaFailure256::GetId() const
{
    return "urma_256";
}
} // namespace diag
