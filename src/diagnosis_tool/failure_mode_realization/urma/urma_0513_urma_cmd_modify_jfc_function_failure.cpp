#include "urma_0513_urma_cmd_modify_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0513UrmaCmdModifyJfcFunctionFailure> g_urma("urma_0513");

bool Urma0513UrmaCmdModifyJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0514", "urma_0515"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0513UrmaCmdModifyJfcFunctionFailure::GetName() const
{
    return "urma_cmd_modify_jfc 函数故障";
}

std::string Urma0513UrmaCmdModifyJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0513UrmaCmdModifyJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0513UrmaCmdModifyJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0513UrmaCmdModifyJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0513UrmaCmdModifyJfcFunctionFailure::GetId() const
{
    return "urma_0513";
}
} // namespace diag
