#include "urma_0270_send_so_from_snd_queue_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0270SendSoFromSndQueueFunctionFailure> g_urma("urma_0270");

bool Urma0270SendSoFromSndQueueFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0271"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0270SendSoFromSndQueueFunctionFailure::GetName() const
{
    return "send_so_from_snd_queue 函数故障";
}

std::string Urma0270SendSoFromSndQueueFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0270SendSoFromSndQueueFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0270SendSoFromSndQueueFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0270SendSoFromSndQueueFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0270SendSoFromSndQueueFunctionFailure::GetId() const
{
    return "urma_0270";
}
} // namespace diag
