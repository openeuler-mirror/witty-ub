#include "urma_failure_594.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure594> g_urma("urma_594");

bool UrmaFailure594::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jetty_batch") != std::string::npos &&
           message.find("Failed to delete jetty batch, ret:") != std::string::npos;
}

std::string UrmaFailure594::GetName() const
{
    return "下层资源删除失败导致删除Jetty失败";
}

std::string UrmaFailure594::GetRootCauseDesc() const
{
    return "urma_delete_jetty_batch清理Jetty时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure594::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure594::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure594::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty_batch，Failed to delete jetty batch, ret:。";
}

std::string UrmaFailure594::GetId() const
{
    return "urma_594";
}
} // namespace diag
