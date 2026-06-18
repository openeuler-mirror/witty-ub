#include "urma_failure_699.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure699> g_urma("urma_699");

bool UrmaFailure699::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_set_jetty_opt") != std::string::npos &&
           message.find("jetty->jetty_cfg.shared.jfr is not exist") != std::string::npos;
}

std::string UrmaFailure699::GetName() const
{
    return "Jetty状态不满足要求导致设置Jetty失败";
}

std::string UrmaFailure699::GetRootCauseDesc() const
{
    return "urma_cmd_set_jetty_opt执行设置Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure699::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure699::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure699::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jetty_opt，jetty->jetty_cfg.shared.jfr is not exist。";
}

std::string UrmaFailure699::GetId() const
{
    return "urma_699";
}
} // namespace diag
