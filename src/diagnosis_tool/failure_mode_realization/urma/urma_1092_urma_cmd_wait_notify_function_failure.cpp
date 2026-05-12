#include "urma_1092_urma_cmd_wait_notify_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1092UrmaCmdWaitNotifyFunctionFailure> g_urma("urma_1092");

bool Urma1092UrmaCmdWaitNotifyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1093"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1092UrmaCmdWaitNotifyFunctionFailure::GetName() const
{
    return "urma_cmd_wait_notify 函数故障";
}

std::string Urma1092UrmaCmdWaitNotifyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1092UrmaCmdWaitNotifyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1092UrmaCmdWaitNotifyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1092UrmaCmdWaitNotifyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1092UrmaCmdWaitNotifyFunctionFailure::GetId() const
{
    return "urma_1092";
}
} // namespace diag
