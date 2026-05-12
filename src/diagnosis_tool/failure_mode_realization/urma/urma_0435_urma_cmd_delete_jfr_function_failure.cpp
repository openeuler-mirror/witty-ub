#include "urma_0435_urma_cmd_delete_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0435UrmaCmdDeleteJfrFunctionFailure> g_urma("urma_0435");

bool Urma0435UrmaCmdDeleteJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0436", "urma_0437"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0435UrmaCmdDeleteJfrFunctionFailure::GetName() const
{
    return "urma_cmd_delete_jfr 函数故障";
}

std::string Urma0435UrmaCmdDeleteJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0435UrmaCmdDeleteJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0435UrmaCmdDeleteJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0435UrmaCmdDeleteJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0435UrmaCmdDeleteJfrFunctionFailure::GetId() const
{
    return "urma_0435";
}
} // namespace diag
