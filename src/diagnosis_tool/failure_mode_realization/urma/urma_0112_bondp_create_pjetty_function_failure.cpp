#include "urma_0112_bondp_create_pjetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0112BondpCreatePjettyFunctionFailure> g_urma("urma_0112");

bool Urma0112BondpCreatePjettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0113"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0112BondpCreatePjettyFunctionFailure::GetName() const
{
    return "bondp_create_pjetty 函数故障";
}

std::string Urma0112BondpCreatePjettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0112BondpCreatePjettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0112BondpCreatePjettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0112BondpCreatePjettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0112BondpCreatePjettyFunctionFailure::GetId() const
{
    return "urma_0112";
}
} // namespace diag
