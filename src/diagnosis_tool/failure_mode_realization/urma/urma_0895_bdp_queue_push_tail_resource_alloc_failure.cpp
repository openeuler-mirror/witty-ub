#include "urma_0895_bdp_queue_push_tail_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0895BdpQueuePushTailResourceAllocFailure> g_urma("urma_0895");

bool Urma0895BdpQueuePushTailResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc bdp_queue_node"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0895BdpQueuePushTailResourceAllocFailure::GetName() const
{
    return "bdp_queue_push_tail 分配资源失败";
}

std::string Urma0895BdpQueuePushTailResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 BDP_QUEUE_ALLOC_ERR";
}

RootCause Urma0895BdpQueuePushTailResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0895BdpQueuePushTailResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0895BdpQueuePushTailResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc bdp_queue_node";
}

std::string Urma0895BdpQueuePushTailResourceAllocFailure::GetId() const
{
    return "urma_0895";
}
} // namespace diag
