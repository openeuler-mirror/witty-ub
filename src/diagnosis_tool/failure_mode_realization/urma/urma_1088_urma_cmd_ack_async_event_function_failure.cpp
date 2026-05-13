#include "urma_1088_urma_cmd_ack_async_event_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1088UrmaCmdAckAsyncEventFunctionFailure> g_urma("urma_1088");

bool Urma1088UrmaCmdAckAsyncEventFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1089"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1088UrmaCmdAckAsyncEventFunctionFailure::GetName() const
{
    return "urma_cmd_ack_async_event 函数故障";
}

std::string Urma1088UrmaCmdAckAsyncEventFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1088UrmaCmdAckAsyncEventFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1088UrmaCmdAckAsyncEventFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1088UrmaCmdAckAsyncEventFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1088UrmaCmdAckAsyncEventFunctionFailure::GetId() const
{
    return "urma_1088";
}
} // namespace diag
