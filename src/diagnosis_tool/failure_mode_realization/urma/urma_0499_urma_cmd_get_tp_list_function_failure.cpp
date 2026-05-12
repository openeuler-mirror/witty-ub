#include "urma_0499_urma_cmd_get_tp_list_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0499UrmaCmdGetTpListFunctionFailure> g_urma("urma_0499");

bool Urma0499UrmaCmdGetTpListFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0500"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0499UrmaCmdGetTpListFunctionFailure::GetName() const
{
    return "urma_cmd_get_tp_list 函数故障";
}

std::string Urma0499UrmaCmdGetTpListFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0499UrmaCmdGetTpListFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0499UrmaCmdGetTpListFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0499UrmaCmdGetTpListFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0499UrmaCmdGetTpListFunctionFailure::GetId() const
{
    return "urma_0499";
}
} // namespace diag
