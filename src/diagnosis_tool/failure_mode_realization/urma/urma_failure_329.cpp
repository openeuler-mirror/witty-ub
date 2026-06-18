#include "urma_failure_329.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure329> g_urma("urma_329");

bool UrmaFailure329::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_free_token_id") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure329::GetName() const
{
    return "token_id、URMA context、dev_fd无效导致释放Token ID、ID失败";
}

std::string UrmaFailure329::GetRootCauseDesc() const
{
    return "urma_cmd_free_token_id用于释放Token ID、ID，调用方传入的token_id、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure329::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure329::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure329::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_token_id，Invalid parameter。";
}

std::string UrmaFailure329::GetId() const
{
    return "urma_329";
}
} // namespace diag
