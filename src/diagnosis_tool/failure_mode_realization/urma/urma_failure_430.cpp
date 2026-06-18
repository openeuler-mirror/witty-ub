#include "urma_failure_430.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure430> g_urma("urma_430");

bool UrmaFailure430::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_active_jfc") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure430::GetName() const
{
    return "JFC、URMA context、dev_fd无效导致激活JFC失败";
}

std::string UrmaFailure430::GetRootCauseDesc() const
{
    return "urma_cmd_active_jfc用于激活JFC，调用方传入的JFC、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure430::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure430::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure430::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_active_jfc，Invalid parameter。";
}

std::string UrmaFailure430::GetId() const
{
    return "urma_430";
}
} // namespace diag
