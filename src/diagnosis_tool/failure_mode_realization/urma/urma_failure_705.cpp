#include "urma_failure_705.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure705> g_urma("urma_705");

bool UrmaFailure705::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_wait_notify") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure705::GetName() const
{
    return "ret无效导致WAIT、notify失败";
}

std::string UrmaFailure705::GetRootCauseDesc() const
{
    return "urma_cmd_wait_notify用于WAIT、notify，调用方传入的ret不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure705::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure705::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure705::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_wait_notify，Invalid parameter。";
}

std::string UrmaFailure705::GetId() const
{
    return "urma_705";
}
} // namespace diag
