#include "urma_failure_438.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure438> g_urma("urma_438");

bool UrmaFailure438::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_set_jetty_opt") != std::string::npos &&
           message.find("jetty->jetty_cfg.jfs_cfg.jfc is not exist") != std::string::npos;
}

std::string UrmaFailure438::GetName() const
{
    return "Jetty状态不满足要求导致设置Jetty失败";
}

std::string UrmaFailure438::GetRootCauseDesc() const
{
    return "urma_cmd_set_jetty_opt执行设置Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure438::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure438::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure438::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jetty_opt，jetty->jetty_cfg.jfs_cfg.jfc is not exist。";
}

std::string UrmaFailure438::GetId() const
{
    return "urma_438";
}
} // namespace diag
