#include "urma_failure_703.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure703> g_urma("urma_703");

bool UrmaFailure703::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_ack_async_event") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure703::GetName() const
{
    return "异步事件无效导致ACK、event失败";
}

std::string UrmaFailure703::GetRootCauseDesc() const
{
    return "urma_cmd_ack_async_event用于ACK、event，调用方传入的异步事件不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure703::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure703::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure703::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_ack_async_event，Invalid parameter。";
}

std::string UrmaFailure703::GetId() const
{
    return "urma_703";
}
} // namespace diag
