#include "urma_failure_439.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure439> g_urma("urma_439");

bool UrmaFailure439::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_wait_jfc") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure439::GetName() const
{
    return "jfce_fd、JFC无效导致WAIT、JFC失败";
}

std::string UrmaFailure439::GetRootCauseDesc() const
{
    return "urma_cmd_wait_jfc用于WAIT、JFC，调用方传入的jfce_fd、JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure439::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure439::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure439::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_wait_jfc，Invalid parameter。";
}

std::string UrmaFailure439::GetId() const
{
    return "urma_439";
}
} // namespace diag
