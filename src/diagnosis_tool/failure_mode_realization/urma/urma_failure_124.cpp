#include "urma_failure_124.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure124> g_urma("urma_124");

bool UrmaFailure124::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_tpn") != std::string::npos && message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure124::GetName() const
{
    return "Jetty无效导致获取TPN失败";
}

std::string UrmaFailure124::GetRootCauseDesc() const
{
    return "urma_get_tpn用于获取TPN，调用方传入的Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure124::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure124::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure124::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_tpn，Invalid parameter.。";
}

std::string UrmaFailure124::GetId() const
{
    return "urma_124";
}
} // namespace diag
