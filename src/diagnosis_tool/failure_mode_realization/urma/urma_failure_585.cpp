#include "urma_failure_585.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure585> g_urma("urma_585");

bool UrmaFailure585::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jetty_to_jetty_grp") != std::string::npos &&
           message.find("failed to delete jetty to jetty_grp.") != std::string::npos;
}

std::string UrmaFailure585::GetName() const
{
    return "下层资源删除失败导致删除Jetty、Jetty组失败";
}

std::string UrmaFailure585::GetRootCauseDesc() const
{
    return "urma_delete_jetty_to_jetty_"
           "grp清理Jetty、Jetty组时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure585::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure585::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure585::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty_to_jetty_grp，failed to delete jetty to jetty_grp.。";
}

std::string UrmaFailure585::GetId() const
{
    return "urma_585";
}
} // namespace diag
