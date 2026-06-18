#include "urma_failure_169.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure169> g_urma("urma_169");

bool UrmaFailure169::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_context") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure169::GetName() const
{
    return "URMA context、配置参数、dev_fd、URMA设备无效导致创建context失败";
}

std::string UrmaFailure169::GetRootCauseDesc() const
{
    return "urma_cmd_create_context用于创建context，调用方传入的URMA "
           "context、配置参数、dev_fd、URMA设备不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure169::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure169::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure169::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_context，Invalid parameter。";
}

std::string UrmaFailure169::GetId() const
{
    return "urma_169";
}
} // namespace diag
