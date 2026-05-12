#include "urma_0207_bondp_create_comp_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0207BondpCreateCompFunctionFailure> g_urma("urma_0207");

bool Urma0207BondpCreateCompFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0208", "urma_0209", "urma_0210"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0207BondpCreateCompFunctionFailure::GetName() const
{
    return "bondp_create_comp 函数故障";
}

std::string Urma0207BondpCreateCompFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0207BondpCreateCompFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0207BondpCreateCompFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0207BondpCreateCompFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0207BondpCreateCompFunctionFailure::GetId() const
{
    return "urma_0207";
}
} // namespace diag
