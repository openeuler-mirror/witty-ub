#include "urma_failure_700.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure700> g_urma("urma_700");

bool UrmaFailure700::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_set_jetty_opt") != std::string::npos &&
           message.find("jetty->jetty_cfg.jetty_grp is not exist") != std::string::npos;
}

std::string UrmaFailure700::GetName() const
{
    return "Jetty状态不满足要求导致设置Jetty失败";
}

std::string UrmaFailure700::GetRootCauseDesc() const
{
    return "urma_cmd_set_jetty_opt执行设置Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure700::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure700::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure700::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jetty_opt，jetty->jetty_cfg.jetty_grp is not exist。";
}

std::string UrmaFailure700::GetId() const
{
    return "urma_700";
}
} // namespace diag
