#include "urma_0432_urma_cmd_delete_jfc_batch_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0432UrmaCmdDeleteJfcBatchResourceAllocFailure> g_urma("urma_0432");

bool Urma0432UrmaCmdDeleteJfcBatchResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to malloc buffer."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0432UrmaCmdDeleteJfcBatchResourceAllocFailure::GetName() const
{
    return "urma_cmd_delete_jfc_batch 分配资源失败";
}

std::string Urma0432UrmaCmdDeleteJfcBatchResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 URMA_ENOMEM";
}

RootCause Urma0432UrmaCmdDeleteJfcBatchResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0432UrmaCmdDeleteJfcBatchResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0432UrmaCmdDeleteJfcBatchResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to malloc buffer.";
}

std::string Urma0432UrmaCmdDeleteJfcBatchResourceAllocFailure::GetId() const
{
    return "urma_0432";
}
} // namespace diag
