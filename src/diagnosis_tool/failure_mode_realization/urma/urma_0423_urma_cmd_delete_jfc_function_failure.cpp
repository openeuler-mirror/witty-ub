#include "urma_0423_urma_cmd_delete_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0423UrmaCmdDeleteJfcFunctionFailure> g_urma("urma_0423");

bool Urma0423UrmaCmdDeleteJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0424", "urma_0425", "urma_0426"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0423UrmaCmdDeleteJfcFunctionFailure::GetName() const
{
    return "urma_cmd_delete_jfc 函数故障";
}

std::string Urma0423UrmaCmdDeleteJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0423UrmaCmdDeleteJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0423UrmaCmdDeleteJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0423UrmaCmdDeleteJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0423UrmaCmdDeleteJfcFunctionFailure::GetId() const
{
    return "urma_0423";
}
} // namespace diag
