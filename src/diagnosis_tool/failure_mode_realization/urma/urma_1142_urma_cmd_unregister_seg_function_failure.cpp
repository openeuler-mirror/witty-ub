#include "urma_1142_urma_cmd_unregister_seg_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1142UrmaCmdUnregisterSegFunctionFailure> g_urma("urma_1142");

bool Urma1142UrmaCmdUnregisterSegFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1143", "urma_1144"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1142UrmaCmdUnregisterSegFunctionFailure::GetName() const
{
    return "urma_cmd_unregister_seg 函数故障";
}

std::string Urma1142UrmaCmdUnregisterSegFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1142UrmaCmdUnregisterSegFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1142UrmaCmdUnregisterSegFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1142UrmaCmdUnregisterSegFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1142UrmaCmdUnregisterSegFunctionFailure::GetId() const
{
    return "urma_1142";
}
} // namespace diag
