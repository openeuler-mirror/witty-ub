#include "urma_failure_464.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure464> g_urma("urma_464");

bool UrmaFailure464::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_jfc_opt") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure464::GetName() const
{
    return "JFC无效导致获取JFC失败";
}

std::string UrmaFailure464::GetRootCauseDesc() const
{
    return "urma_get_jfc_opt用于获取JFC，调用方传入的JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure464::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure464::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure464::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jfc_opt，Invalid parameter.。";
}

std::string UrmaFailure464::GetId() const
{
    return "urma_464";
}
} // namespace diag
