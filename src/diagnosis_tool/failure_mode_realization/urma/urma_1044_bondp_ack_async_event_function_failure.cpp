#include "urma_1044_bondp_ack_async_event_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1044BondpAckAsyncEventFunctionFailure> g_urma("urma_1044");

bool Urma1044BondpAckAsyncEventFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1045"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1044BondpAckAsyncEventFunctionFailure::GetName() const
{
    return "bondp_ack_async_event 函数故障";
}

std::string Urma1044BondpAckAsyncEventFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1044BondpAckAsyncEventFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1044BondpAckAsyncEventFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1044BondpAckAsyncEventFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1044BondpAckAsyncEventFunctionFailure::GetId() const
{
    return "urma_1044";
}
} // namespace diag
