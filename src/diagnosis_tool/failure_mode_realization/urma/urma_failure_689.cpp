#include "urma_failure_689.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure689> g_urma("urma_689");

bool UrmaFailure689::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_active_jfs") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure689::GetName() const
{
    return "JFS、URMA context、dev_fd无效导致激活JFS失败";
}

std::string UrmaFailure689::GetRootCauseDesc() const
{
    return "urma_cmd_active_jfs用于激活JFS，调用方传入的JFS、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure689::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure689::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure689::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_active_jfs，Invalid parameter。";
}

std::string UrmaFailure689::GetId() const
{
    return "urma_689";
}
} // namespace diag
