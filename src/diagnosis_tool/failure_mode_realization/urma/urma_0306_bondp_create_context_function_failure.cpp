#include "urma_0306_bondp_create_context_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0306BondpCreateContextFunctionFailure> g_urma("urma_0306");

bool Urma0306BondpCreateContextFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0307", "urma_0308", "urma_0309", "urma_0310", "urma_0311"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0306BondpCreateContextFunctionFailure::GetName() const
{
    return "bondp_create_context 函数故障";
}

std::string Urma0306BondpCreateContextFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0306BondpCreateContextFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0306BondpCreateContextFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0306BondpCreateContextFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0306BondpCreateContextFunctionFailure::GetId() const
{
    return "urma_0306";
}
} // namespace diag
