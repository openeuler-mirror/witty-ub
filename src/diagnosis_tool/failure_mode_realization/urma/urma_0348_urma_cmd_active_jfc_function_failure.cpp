#include "urma_0348_urma_cmd_active_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0348UrmaCmdActiveJfcFunctionFailure> g_urma("urma_0348");

bool Urma0348UrmaCmdActiveJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0349", "urma_0350"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0348UrmaCmdActiveJfcFunctionFailure::GetName() const
{
    return "urma_cmd_active_jfc 函数故障";
}

std::string Urma0348UrmaCmdActiveJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0348UrmaCmdActiveJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0348UrmaCmdActiveJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0348UrmaCmdActiveJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0348UrmaCmdActiveJfcFunctionFailure::GetId() const
{
    return "urma_0348";
}
} // namespace diag
