#include "urma_failure_724.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure724> g_urma("urma_724");

bool UrmaFailure724::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jfr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure724::GetName() const
{
    return "JFR无效导致激活JFR失败";
}

std::string UrmaFailure724::GetRootCauseDesc() const
{
    return "urma_active_jfr用于激活JFR，调用方传入的JFR不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure724::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure724::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure724::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfr，Invalid parameter.。";
}

std::string UrmaFailure724::GetId() const
{
    return "urma_724";
}
} // namespace diag
