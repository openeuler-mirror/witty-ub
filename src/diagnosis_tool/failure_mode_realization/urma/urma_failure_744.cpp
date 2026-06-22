#include "urma_failure_744.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure744> g_urma("urma_744");

bool UrmaFailure744::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_ack_async_event") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure744::GetName() const
{
    return "provider未提供get_async_event操作实现无效导致ackACK、event失败";
}

std::string UrmaFailure744::GetRootCauseDesc() const
{
    return "urma_ack_async_event用于ackACK、event，调用方传入的provider未提供get_async_"
           "event操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure744::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure744::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure744::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ack_async_event，Invalid parameter.。";
}

std::string UrmaFailure744::GetId() const
{
    return "urma_744";
}
} // namespace diag
