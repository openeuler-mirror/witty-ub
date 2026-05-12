#include "urma_0019_bondp_init_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0019BondpInitFunctionFailure> g_urma("urma_0019");

bool Urma0019BondpInitFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0020", "urma_0021"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0019BondpInitFunctionFailure::GetName() const
{
    return "bondp_init 函数故障";
}

std::string Urma0019BondpInitFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0019BondpInitFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0019BondpInitFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0019BondpInitFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0019BondpInitFunctionFailure::GetId() const
{
    return "urma_0019";
}
} // namespace diag
