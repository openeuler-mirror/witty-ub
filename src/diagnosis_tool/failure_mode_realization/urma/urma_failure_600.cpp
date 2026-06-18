#include "urma_failure_600.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure600> g_urma("urma_600");

bool UrmaFailure600::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_notifier") != std::string::npos &&
           message.find("Failed to delete notifier, ret:") != std::string::npos;
}

std::string UrmaFailure600::GetName() const
{
    return "下层资源删除失败导致删除Notifier失败";
}

std::string UrmaFailure600::GetRootCauseDesc() const
{
    return "urma_delete_notifier清理Notifier时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure600::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure600::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure600::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_notifier，Failed to delete notifier, ret:。";
}

std::string UrmaFailure600::GetId() const
{
    return "urma_600";
}
} // namespace diag
