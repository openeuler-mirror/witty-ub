#include "urma_0812_urma_modify_tp_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0812UrmaModifyTpFunctionFailure> g_urma("urma_0812");

bool Urma0812UrmaModifyTpFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0813"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0812UrmaModifyTpFunctionFailure::GetName() const
{
    return "urma_modify_tp 函数故障";
}

std::string Urma0812UrmaModifyTpFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0812UrmaModifyTpFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0812UrmaModifyTpFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0812UrmaModifyTpFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0812UrmaModifyTpFunctionFailure::GetId() const
{
    return "urma_0812";
}
} // namespace diag
