#include "urma_0022_bondp_init_ctx_table_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0022BondpInitCtxTableFunctionFailure> g_urma("urma_0022");

bool Urma0022BondpInitCtxTableFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0023", "urma_0024", "urma_0025"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0022BondpInitCtxTableFunctionFailure::GetName() const
{
    return "bondp_init_ctx_table 函数故障";
}

std::string Urma0022BondpInitCtxTableFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0022BondpInitCtxTableFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0022BondpInitCtxTableFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0022BondpInitCtxTableFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0022BondpInitCtxTableFunctionFailure::GetId() const
{
    return "urma_0022";
}
} // namespace diag
