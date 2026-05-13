#include "urma_0454_urma_cmd_delete_jfs_batch_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0454UrmaCmdDeleteJfsBatchResourceAllocFailure> g_urma("urma_0454");

bool Urma0454UrmaCmdDeleteJfsBatchResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to malloc buffer."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0454UrmaCmdDeleteJfsBatchResourceAllocFailure::GetName() const
{
    return "urma_cmd_delete_jfs_batch 分配资源失败";
}

std::string Urma0454UrmaCmdDeleteJfsBatchResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 URMA_ENOMEM";
}

RootCause Urma0454UrmaCmdDeleteJfsBatchResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0454UrmaCmdDeleteJfsBatchResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0454UrmaCmdDeleteJfsBatchResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to malloc buffer.";
}

std::string Urma0454UrmaCmdDeleteJfsBatchResourceAllocFailure::GetId() const
{
    return "urma_0454";
}
} // namespace diag
