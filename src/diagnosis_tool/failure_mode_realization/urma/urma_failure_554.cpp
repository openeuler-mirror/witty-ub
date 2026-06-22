#include "urma_failure_554.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure554> g_urma("urma_554");

bool UrmaFailure554::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jetty_grp") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure554::GetName() const
{
    return "jetty_grp、URMA context、dev_fd无效导致删除Jetty组失败";
}

std::string UrmaFailure554::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jetty_grp用于删除Jetty组，调用方传入的jetty_grp、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure554::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure554::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure554::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jetty_grp，Invalid parameter。";
}

std::string UrmaFailure554::GetId() const
{
    return "urma_554";
}
} // namespace diag
