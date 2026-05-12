#include "urma_1103_urma_ack_notify_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1103UrmaAckNotifyFunctionFailure> g_urma("urma_1103");

bool Urma1103UrmaAckNotifyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1104"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1103UrmaAckNotifyFunctionFailure::GetName() const
{
    return "urma_ack_notify 函数故障";
}

std::string Urma1103UrmaAckNotifyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1103UrmaAckNotifyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1103UrmaAckNotifyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1103UrmaAckNotifyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1103UrmaAckNotifyFunctionFailure::GetId() const
{
    return "urma_1103";
}
} // namespace diag
