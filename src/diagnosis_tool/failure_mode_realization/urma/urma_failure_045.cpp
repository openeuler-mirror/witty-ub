#include "urma_failure_045.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure045> g_urma("urma_045");

bool UrmaFailure045::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_unregister_provider_ops") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure045::GetName() const
{
    return "provider_ops、名称无效导致注销provider、OPS失败";
}

std::string UrmaFailure045::GetRootCauseDesc() const
{
    return "urma_unregister_provider_ops用于注销provider、OPS，调用方传入的provider_"
           "ops、名称不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure045::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure045::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure045::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unregister_provider_ops，Invalid parameter.。";
}

std::string UrmaFailure045::GetId() const
{
    return "urma_045";
}
} // namespace diag
