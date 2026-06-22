#include "urma_failure_632.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure632> g_urma("urma_632");

bool UrmaFailure632::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_async_event") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure632::GetName() const
{
    return "URMA context、async_fd、异步事件无效导致获取event失败";
}

std::string UrmaFailure632::GetRootCauseDesc() const
{
    return "urma_cmd_get_async_event用于获取event，调用方传入的URMA "
           "context、async_fd、异步事件不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure632::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure632::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure632::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_async_event，Invalid parameter。";
}

std::string UrmaFailure632::GetId() const
{
    return "urma_632";
}
} // namespace diag
