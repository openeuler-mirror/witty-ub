#include "urma_failure_342.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure342> g_urma("urma_342");

bool UrmaFailure342::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_token_id") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure342::GetName() const
{
    return "URMA context无效导致分配Token ID、ID失败";
}

std::string UrmaFailure342::GetRootCauseDesc() const
{
    return "urma_alloc_token_id用于分配Token ID、ID，调用方传入的URMA context不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure342::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure342::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure342::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_token_id，Invalid parameter.。";
}

std::string UrmaFailure342::GetId() const
{
    return "urma_342";
}
} // namespace diag
