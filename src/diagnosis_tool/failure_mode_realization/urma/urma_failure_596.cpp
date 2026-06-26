#include "urma_failure_596.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure596> g_urma("urma_596");

bool UrmaFailure596::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_deactive_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure596::GetName() const
{
    return "Jetty无效导致去激活Jetty失败";
}

std::string UrmaFailure596::GetRootCauseDesc() const
{
    return "urma_deactive_jetty用于去激活Jetty，调用方传入的Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure596::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure596::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure596::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jetty，Invalid parameter.。";
}

std::string UrmaFailure596::GetId() const
{
    return "urma_596";
}
} // namespace diag
