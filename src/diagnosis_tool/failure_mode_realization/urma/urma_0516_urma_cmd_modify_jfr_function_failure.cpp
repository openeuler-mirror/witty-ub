#include "urma_0516_urma_cmd_modify_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0516UrmaCmdModifyJfrFunctionFailure> g_urma("urma_0516");

bool Urma0516UrmaCmdModifyJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0517", "urma_0518"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0516UrmaCmdModifyJfrFunctionFailure::GetName() const
{
    return "urma_cmd_modify_jfr 函数故障";
}

std::string Urma0516UrmaCmdModifyJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0516UrmaCmdModifyJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0516UrmaCmdModifyJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0516UrmaCmdModifyJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0516UrmaCmdModifyJfrFunctionFailure::GetId() const
{
    return "urma_0516";
}
} // namespace diag
