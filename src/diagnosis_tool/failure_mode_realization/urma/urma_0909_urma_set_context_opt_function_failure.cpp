#include "urma_0909_urma_set_context_opt_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0909UrmaSetContextOptFunctionFailure> g_urma("urma_0909");

bool Urma0909UrmaSetContextOptFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0910", "urma_0911", "urma_0912", "urma_0913"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0909UrmaSetContextOptFunctionFailure::GetName() const
{
    return "urma_set_context_opt 函数故障";
}

std::string Urma0909UrmaSetContextOptFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0909UrmaSetContextOptFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0909UrmaSetContextOptFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0909UrmaSetContextOptFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0909UrmaSetContextOptFunctionFailure::GetId() const
{
    return "urma_0909";
}
} // namespace diag
