#include "urma_failure_746.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure746> g_urma("urma_746");

bool UrmaFailure746::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_user_ctl") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure746::GetName() const
{
    return "provider操作表、ack_async_event无效导致userUSER、CTL失败";
}

std::string UrmaFailure746::GetRootCauseDesc() const
{
    return "urma_user_ctl用于userUSER、CTL，调用方传入的provider操作表、ack_async_"
           "event不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure746::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure746::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure746::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_user_ctl，Invalid parameter.。";
}

std::string UrmaFailure746::GetId() const
{
    return "urma_746";
}
} // namespace diag
