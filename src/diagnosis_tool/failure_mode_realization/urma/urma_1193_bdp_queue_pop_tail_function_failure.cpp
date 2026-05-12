#include "urma_1193_bdp_queue_pop_tail_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1193BdpQueuePopTailFunctionFailure> g_urma("urma_1193");

bool Urma1193BdpQueuePopTailFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1194"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1193BdpQueuePopTailFunctionFailure::GetName() const
{
    return "bdp_queue_pop_tail 函数故障";
}

std::string Urma1193BdpQueuePopTailFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1193BdpQueuePopTailFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1193BdpQueuePopTailFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1193BdpQueuePopTailFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1193BdpQueuePopTailFunctionFailure::GetId() const
{
    return "urma_1193";
}
} // namespace diag
