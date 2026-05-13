#include "urma_0418_urma_cmd_delete_jetty_batch_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0418UrmaCmdDeleteJettyBatchResourceAllocFailure> g_urma("urma_0418");

bool Urma0418UrmaCmdDeleteJettyBatchResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to malloc buffer."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0418UrmaCmdDeleteJettyBatchResourceAllocFailure::GetName() const
{
    return "urma_cmd_delete_jetty_batch 分配资源失败";
}

std::string Urma0418UrmaCmdDeleteJettyBatchResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 URMA_ENOMEM";
}

RootCause Urma0418UrmaCmdDeleteJettyBatchResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0418UrmaCmdDeleteJettyBatchResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0418UrmaCmdDeleteJettyBatchResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to malloc buffer.";
}

std::string Urma0418UrmaCmdDeleteJettyBatchResourceAllocFailure::GetId() const
{
    return "urma_0418";
}
} // namespace diag
