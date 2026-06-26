#include "urma_failure_265.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure265> g_urma("urma_265");

bool UrmaFailure265::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_async_event") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure265::GetName() const
{
    return "event无效导致获取event失败";
}

std::string UrmaFailure265::GetRootCauseDesc() const
{
    return "urma_get_async_event用于获取event，调用方传入的event不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure265::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure265::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure265::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_async_event，Invalid parameter.。";
}

std::string UrmaFailure265::GetId() const
{
    return "urma_265";
}
} // namespace diag
