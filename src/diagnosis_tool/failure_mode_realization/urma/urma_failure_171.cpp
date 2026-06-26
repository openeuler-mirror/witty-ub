#include "urma_failure_171.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure171> g_urma("urma_171");

bool UrmaFailure171::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_jfs") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure171::GetName() const
{
    return "URMA context、dev_fd、JFS、配置参数无效导致创建JFS失败";
}

std::string UrmaFailure171::GetRootCauseDesc() const
{
    return "urma_cmd_create_jfs用于创建JFS，调用方传入的URMA "
           "context、dev_fd、JFS、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure171::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure171::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure171::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jfs，Invalid parameter。";
}

std::string UrmaFailure171::GetId() const
{
    return "urma_171";
}
} // namespace diag
