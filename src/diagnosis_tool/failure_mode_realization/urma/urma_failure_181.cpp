#include "urma_failure_181.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure181> g_urma("urma_181");

bool UrmaFailure181::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_jetty_grp") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure181::GetName() const
{
    return "URMA context、dev_fd、jetty_grp、配置参数无效导致创建Jetty组失败";
}

std::string UrmaFailure181::GetRootCauseDesc() const
{
    return "urma_cmd_create_jetty_grp用于创建Jetty组，调用方传入的URMA "
           "context、dev_fd、jetty_grp、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure181::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure181::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure181::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jetty_grp，Invalid parameter。";
}

std::string UrmaFailure181::GetId() const
{
    return "urma_181";
}
} // namespace diag
