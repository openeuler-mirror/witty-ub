#include "urma_failure_732.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure732> g_urma("urma_732");

bool UrmaFailure732::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jetty_opt") != std::string::npos &&
           message.find("Failed to set opt, jetty has been activated") != std::string::npos;
}

std::string UrmaFailure732::GetName() const
{
    return "设置Jetty执行失败导致设置Jetty失败";
}

std::string UrmaFailure732::GetRootCauseDesc() const
{
    return "urma_set_jetty_opt执行设置Jetty时依赖的设置Jetty步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure732::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure732::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure732::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jetty_opt，Failed to set opt, jetty has been activated。";
}

std::string UrmaFailure732::GetId() const
{
    return "urma_732";
}
} // namespace diag
