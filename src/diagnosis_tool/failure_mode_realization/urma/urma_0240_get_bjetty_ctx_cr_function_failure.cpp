#include "urma_0240_get_bjetty_ctx_cr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0240GetBjettyCtxCrFunctionFailure> g_urma("urma_0240");

bool Urma0240GetBjettyCtxCrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0241", "urma_0242"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0240GetBjettyCtxCrFunctionFailure::GetName() const
{
    return "get_bjetty_ctx_by_cr 函数故障";
}

std::string Urma0240GetBjettyCtxCrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0240GetBjettyCtxCrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0240GetBjettyCtxCrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0240GetBjettyCtxCrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0240GetBjettyCtxCrFunctionFailure::GetId() const
{
    return "urma_0240";
}
} // namespace diag
