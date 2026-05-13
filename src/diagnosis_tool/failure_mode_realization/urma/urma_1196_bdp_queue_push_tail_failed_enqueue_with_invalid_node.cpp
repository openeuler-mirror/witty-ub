#include "urma_1196_bdp_queue_push_tail_failed_enqueue_with_invalid_node.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1196BdpQueuePushTailFailedEnqueueWithInvalidNode> g_urma("urma_1196");

bool Urma1196BdpQueuePushTailFailedEnqueueWithInvalidNode::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to enqueue with invalid node_num: %, max_node: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1196BdpQueuePushTailFailedEnqueueWithInvalidNode::GetName() const
{
    return "bdp_queue_push_tail Failed to enqueue with invalid node_";
}

std::string Urma1196BdpQueuePushTailFailedEnqueueWithInvalidNode::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `q->node_num >= q->max_node`；该路径返回 -1";
}

RootCause Urma1196BdpQueuePushTailFailedEnqueueWithInvalidNode::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1196BdpQueuePushTailFailedEnqueueWithInvalidNode::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1196BdpQueuePushTailFailedEnqueueWithInvalidNode::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to enqueue with invalid node_num: %, max_node: %.";
}

std::string Urma1196BdpQueuePushTailFailedEnqueueWithInvalidNode::GetId() const
{
    return "urma_1196";
}
} // namespace diag
