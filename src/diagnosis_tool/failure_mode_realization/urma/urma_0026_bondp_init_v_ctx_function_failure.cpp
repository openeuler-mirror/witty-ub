#include "urma_0026_bondp_init_v_ctx_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0026BondpInitVCtxFunctionFailure> g_urma("urma_0026");

bool Urma0026BondpInitVCtxFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0027"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0026BondpInitVCtxFunctionFailure::GetName() const
{
    return "bondp_init_v_ctx 函数故障";
}

std::string Urma0026BondpInitVCtxFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0026BondpInitVCtxFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0026BondpInitVCtxFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0026BondpInitVCtxFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0026BondpInitVCtxFunctionFailure::GetId() const
{
    return "urma_0026";
}
} // namespace diag
