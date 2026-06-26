#include "urma_failure_208.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure208> g_urma("urma_208");

bool UrmaFailure208::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jetty_opt") != std::string::npos &&
           message.find("Failed to exec urma_add_jetty_to_jetty_grp.") != std::string::npos;
}

std::string UrmaFailure208::GetName() const
{
    return "设置Jetty执行失败导致设置Jetty失败";
}

std::string UrmaFailure208::GetRootCauseDesc() const
{
    return "urma_set_jetty_opt执行设置Jetty时依赖的设置Jetty步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure208::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure208::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure208::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jetty_opt，Failed to exec urma_add_jetty_to_jetty_grp.。";
}

std::string UrmaFailure208::GetId() const
{
    return "urma_208";
}
} // namespace diag
