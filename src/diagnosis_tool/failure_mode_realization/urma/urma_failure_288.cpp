#include "urma_failure_288.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure288> g_urma("urma_288");

bool UrmaFailure288::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_uasid") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure288::GetName() const
{
    return "uasid无效导致获取uasid失败";
}

std::string UrmaFailure288::GetRootCauseDesc() const
{
    return "urma_get_uasid用于获取uasid，调用方传入的uasid不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure288::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure288::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure288::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_uasid，Invalid parameter.。";
}

std::string UrmaFailure288::GetId() const
{
    return "urma_288";
}
} // namespace diag
