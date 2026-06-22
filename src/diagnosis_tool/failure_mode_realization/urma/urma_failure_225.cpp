#include "urma_failure_225.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure225> g_urma("urma_225");

bool UrmaFailure225::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_get_async_event") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure225::GetName() const
{
    return "URMA context、async_fd、v_event无效导致获取event失败";
}

std::string UrmaFailure225::GetRootCauseDesc() const
{
    return "bondp_get_async_event用于获取event，调用方传入的URMA "
           "context、async_fd、v_event不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure225::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure225::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure225::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_get_async_event，Invalid parameter。";
}

std::string UrmaFailure225::GetId() const
{
    return "urma_225";
}
} // namespace diag
