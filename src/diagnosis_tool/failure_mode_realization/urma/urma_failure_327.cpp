#include "urma_failure_327.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure327> g_urma("urma_327");

bool UrmaFailure327::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_alloc_token_id_ex") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure327::GetName() const
{
    return "URMA context、dev_fd、token_id无效导致分配Token ID、ID失败";
}

std::string UrmaFailure327::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_token_id_ex用于分配Token ID、ID，调用方传入的URMA "
           "context、dev_fd、token_id不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure327::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure327::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure327::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_token_id_ex，Invalid parameter。";
}

std::string UrmaFailure327::GetId() const
{
    return "urma_327";
}
} // namespace diag
