#include "urma_1191_bdp_queue_pop_head_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1191BdpQueuePopHeadFunctionFailure> g_urma("urma_1191");

bool Urma1191BdpQueuePopHeadFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1192"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1191BdpQueuePopHeadFunctionFailure::GetName() const
{
    return "bdp_queue_pop_head 函数故障";
}

std::string Urma1191BdpQueuePopHeadFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1191BdpQueuePopHeadFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1191BdpQueuePopHeadFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1191BdpQueuePopHeadFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1191BdpQueuePopHeadFunctionFailure::GetId() const
{
    return "urma_1191";
}
} // namespace diag
