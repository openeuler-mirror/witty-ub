#include "urma_0304_create_bjetty_ctx_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0304CreateBjettyCtxFunctionFailure> g_urma("urma_0304");

bool Urma0304CreateBjettyCtxFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0305"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0304CreateBjettyCtxFunctionFailure::GetName() const
{
    return "create_bjetty_ctx 函数故障";
}

std::string Urma0304CreateBjettyCtxFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0304CreateBjettyCtxFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0304CreateBjettyCtxFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0304CreateBjettyCtxFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0304CreateBjettyCtxFunctionFailure::GetId() const
{
    return "urma_0304";
}
} // namespace diag
