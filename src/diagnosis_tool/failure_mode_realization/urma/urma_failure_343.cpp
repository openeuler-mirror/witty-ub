#include "urma_failure_343.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure343> g_urma("urma_343");

bool UrmaFailure343::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_token_id_ex") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure343::GetName() const
{
    return "Token ID、ID无效导致分配Token ID、ID失败";
}

std::string UrmaFailure343::GetRootCauseDesc() const
{
    return "urma_alloc_token_id_ex用于分配Token ID、ID，调用方传入的Token ID、ID不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure343::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure343::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure343::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_token_id_ex，Invalid parameter.。";
}

std::string UrmaFailure343::GetId() const
{
    return "urma_343";
}
} // namespace diag
