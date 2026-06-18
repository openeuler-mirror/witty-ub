#include "urma_failure_044.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure044> g_urma("urma_044");

bool UrmaFailure044::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_register_provider_ops") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure044::GetName() const
{
    return "provider_ops、名称无效导致注册provider、OPS失败";
}

std::string UrmaFailure044::GetRootCauseDesc() const
{
    return "urma_register_provider_ops用于注册provider、OPS，调用方传入的provider_"
           "ops、名称不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure044::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure044::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure044::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_register_provider_ops，Invalid parameter.。";
}

std::string UrmaFailure044::GetId() const
{
    return "urma_044";
}
} // namespace diag
