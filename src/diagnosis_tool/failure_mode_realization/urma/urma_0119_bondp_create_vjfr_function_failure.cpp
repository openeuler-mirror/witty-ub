#include "urma_0119_bondp_create_vjfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0119BondpCreateVjfrFunctionFailure> g_urma("urma_0119");

bool Urma0119BondpCreateVjfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0120"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0119BondpCreateVjfrFunctionFailure::GetName() const
{
    return "bondp_create_vjfr 函数故障";
}

std::string Urma0119BondpCreateVjfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0119BondpCreateVjfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0119BondpCreateVjfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0119BondpCreateVjfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0119BondpCreateVjfrFunctionFailure::GetId() const
{
    return "urma_0119";
}
} // namespace diag
