#include "urma_failure_745.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure745> g_urma("urma_745");

bool UrmaFailure745::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_ack_async_event") != std::string::npos &&
           message.find("Invalid parameter with ops nullptr.") != std::string::npos;
}

std::string UrmaFailure745::GetName() const
{
    return "异步事件、URMA context无效导致ackACK、event失败";
}

std::string UrmaFailure745::GetRootCauseDesc() const
{
    return "urma_ack_async_event用于ackACK、event，调用方传入的异步事件、URMA "
           "context不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure745::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure745::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure745::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ack_async_event，Invalid parameter with ops nullptr.。";
}

std::string UrmaFailure745::GetId() const
{
    return "urma_745";
}
} // namespace diag
