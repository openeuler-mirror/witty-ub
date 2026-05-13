#include "urma_0894_bdp_queue_push_tail_function_failure_bond_utils_bdp_queue.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0894BdpQueuePushTailFunctionFailureBondUtilsBdpQueue> g_urma("urma_0894");

bool Urma0894BdpQueuePushTailFunctionFailureBondUtilsBdpQueue::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0895"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0894BdpQueuePushTailFunctionFailureBondUtilsBdpQueue::GetName() const
{
    return "bdp_queue_push_tail 函数故障（bond/utils/bdp_queue.c）";
}

std::string Urma0894BdpQueuePushTailFunctionFailureBondUtilsBdpQueue::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0894BdpQueuePushTailFunctionFailureBondUtilsBdpQueue::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0894BdpQueuePushTailFunctionFailureBondUtilsBdpQueue::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0894BdpQueuePushTailFunctionFailureBondUtilsBdpQueue::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0894BdpQueuePushTailFunctionFailureBondUtilsBdpQueue::GetId() const
{
    return "urma_0894";
}
} // namespace diag
