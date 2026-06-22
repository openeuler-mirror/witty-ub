#include "urma_failure_484.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure484> g_urma("urma_484");

bool UrmaFailure484::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_flush_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure484::GetName() const
{
    return "Jetty、cr无效导致刷新Jetty失败";
}

std::string UrmaFailure484::GetRootCauseDesc() const
{
    return "urma_flush_jetty用于刷新Jetty，调用方传入的Jetty、cr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure484::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure484::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure484::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_flush_jetty，Invalid parameter.。";
}

std::string UrmaFailure484::GetId() const
{
    return "urma_484";
}
} // namespace diag
