#include "urma_failure_735.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure735> g_urma("urma_735");

bool UrmaFailure735::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jetty_opt") != std::string::npos &&
           message.find("Failed to exec ops->set_jetty_opt.") != std::string::npos;
}

std::string UrmaFailure735::GetName() const
{
    return "设置Jetty执行失败导致设置Jetty失败";
}

std::string UrmaFailure735::GetRootCauseDesc() const
{
    return "urma_set_jetty_opt执行设置Jetty时依赖的设置Jetty步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure735::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure735::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure735::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jetty_opt，Failed to exec ops->set_jetty_opt.。";
}

std::string UrmaFailure735::GetId() const
{
    return "urma_735";
}
} // namespace diag
