#include "urma_failure_039.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure039> g_urma("urma_039");

bool UrmaFailure039::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_register_log_func") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure039::GetName() const
{
    return "func无效导致注册LOG、FUNC失败";
}

std::string UrmaFailure039::GetRootCauseDesc() const
{
    return "urma_register_log_func用于注册LOG、FUNC，调用方传入的func不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure039::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure039::GetFixSuggDesc() const
{
    return "当前不会触发失败";
}

std::string UrmaFailure039::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_register_log_func，Invalid parameter.。";
}

std::string UrmaFailure039::GetId() const
{
    return "urma_039";
}
} // namespace diag
