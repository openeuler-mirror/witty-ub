#include "urma_failure_532.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure532> g_urma("urma_532");

bool UrmaFailure532::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_deactive_jfs") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure532::GetName() const
{
    return "JFS、URMA context、dev_fd无效导致去激活JFS失败";
}

std::string UrmaFailure532::GetRootCauseDesc() const
{
    return "urma_cmd_deactive_jfs用于去激活JFS，调用方传入的JFS、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure532::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure532::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure532::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_deactive_jfs，Invalid parameter。";
}

std::string UrmaFailure532::GetId() const
{
    return "urma_532";
}
} // namespace diag
