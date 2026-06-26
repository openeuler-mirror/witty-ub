#include "urma_failure_489.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure489> g_urma("urma_489");

bool UrmaFailure489::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_recv") != std::string::npos &&
           message.find("There are invalid parameters.") != std::string::npos;
}

std::string UrmaFailure489::GetName() const
{
    return "URMA资源无效导致接收URMA资源失败";
}

std::string UrmaFailure489::GetRootCauseDesc() const
{
    return "urma_recv用于接收URMA资源，调用方传入的URMA资源不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure489::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure489::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure489::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_recv，There are invalid parameters.。";
}

std::string UrmaFailure489::GetId() const
{
    return "urma_489";
}
} // namespace diag
