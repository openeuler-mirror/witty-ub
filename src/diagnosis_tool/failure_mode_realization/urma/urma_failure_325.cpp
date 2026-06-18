#include "urma_failure_325.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure325> g_urma("urma_325");

bool UrmaFailure325::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_alloc_token_id") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure325::GetName() const
{
    return "URMA context、dev_fd、token_id无效导致分配Token ID、ID失败";
}

std::string UrmaFailure325::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_token_id用于分配Token ID、ID，调用方传入的URMA "
           "context、dev_fd、token_id不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure325::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure325::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure325::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_token_id，Invalid parameter。";
}

std::string UrmaFailure325::GetId() const
{
    return "urma_325";
}
} // namespace diag
