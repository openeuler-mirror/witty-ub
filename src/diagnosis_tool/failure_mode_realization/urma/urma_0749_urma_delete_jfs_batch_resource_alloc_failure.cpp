#include "urma_0749_urma_delete_jfs_batch_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0749UrmaDeleteJfsBatchResourceAllocFailure> g_urma("urma_0749");

bool Urma0749UrmaDeleteJfsBatchResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc memory."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0749UrmaDeleteJfsBatchResourceAllocFailure::GetName() const
{
    return "urma_delete_jfs_batch 分配资源失败";
}

std::string Urma0749UrmaDeleteJfsBatchResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 URMA_ENOMEM";
}

RootCause Urma0749UrmaDeleteJfsBatchResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0749UrmaDeleteJfsBatchResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0749UrmaDeleteJfsBatchResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc memory.";
}

std::string Urma0749UrmaDeleteJfsBatchResourceAllocFailure::GetId() const
{
    return "urma_0749";
}
} // namespace diag
