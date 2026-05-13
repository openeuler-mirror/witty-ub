#include "urma_1094_wait_async_event_ack_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1094WaitAsyncEventAckFunctionFailure> g_urma("urma_1094");

bool Urma1094WaitAsyncEventAckFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1095"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1094WaitAsyncEventAckFunctionFailure::GetName() const
{
    return "wait_async_event_ack 函数故障";
}

std::string Urma1094WaitAsyncEventAckFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1094WaitAsyncEventAckFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1094WaitAsyncEventAckFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1094WaitAsyncEventAckFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1094WaitAsyncEventAckFunctionFailure::GetId() const
{
    return "urma_1094";
}
} // namespace diag
