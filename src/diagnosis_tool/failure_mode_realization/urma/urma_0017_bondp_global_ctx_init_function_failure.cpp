#include "urma_0017_bondp_global_ctx_init_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0017BondpGlobalCtxInitFunctionFailure> g_urma("urma_0017");

bool Urma0017BondpGlobalCtxInitFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0018"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0017BondpGlobalCtxInitFunctionFailure::GetName() const
{
    return "bondp_global_ctx_init 函数故障";
}

std::string Urma0017BondpGlobalCtxInitFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0017BondpGlobalCtxInitFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0017BondpGlobalCtxInitFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0017BondpGlobalCtxInitFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0017BondpGlobalCtxInitFunctionFailure::GetId() const
{
    return "urma_0017";
}
} // namespace diag
