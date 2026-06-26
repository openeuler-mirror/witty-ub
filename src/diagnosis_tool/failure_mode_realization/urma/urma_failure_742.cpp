#include "urma_failure_742.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure742> g_urma("urma_742");

bool UrmaFailure742::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_unadvise_jfr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure742::GetName() const
{
    return "unadvise、JFR无效导致unadviseunadvise、JFR失败";
}

std::string UrmaFailure742::GetRootCauseDesc() const
{
    return "urma_unadvise_"
           "jfr用于unadviseunadvise、JFR，调用方传入的unadvise、JFR不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure742::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure742::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure742::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unadvise_jfr，Invalid parameter.。";
}

std::string UrmaFailure742::GetId() const
{
    return "urma_742";
}
} // namespace diag
