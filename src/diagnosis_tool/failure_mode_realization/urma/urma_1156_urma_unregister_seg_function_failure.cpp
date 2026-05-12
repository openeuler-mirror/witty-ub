#include "urma_1156_urma_unregister_seg_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1156UrmaUnregisterSegFunctionFailure> g_urma("urma_1156");

bool Urma1156UrmaUnregisterSegFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1157", "urma_1158"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1156UrmaUnregisterSegFunctionFailure::GetName() const
{
    return "urma_unregister_seg 函数故障";
}

std::string Urma1156UrmaUnregisterSegFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1156UrmaUnregisterSegFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1156UrmaUnregisterSegFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1156UrmaUnregisterSegFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1156UrmaUnregisterSegFunctionFailure::GetId() const
{
    return "urma_1156";
}
} // namespace diag
