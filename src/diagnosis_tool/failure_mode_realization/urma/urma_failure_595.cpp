#include "urma_failure_595.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure595> g_urma("urma_595");

bool UrmaFailure595::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jetty_opt") != std::string::npos &&
           message.find("Failed to exec urma_delete_jetty_to_jetty_grp.") != std::string::npos;
}

std::string UrmaFailure595::GetName() const
{
    return "下层资源删除失败导致设置Jetty失败";
}

std::string UrmaFailure595::GetRootCauseDesc() const
{
    return "urma_set_jetty_opt清理Jetty时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure595::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure595::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure595::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jetty_opt，Failed to exec urma_delete_jetty_to_jetty_grp.。";
}

std::string UrmaFailure595::GetId() const
{
    return "urma_595";
}
} // namespace diag
