#include "urma_0312_bondp_create_pseg_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0312BondpCreatePsegFunctionFailure> g_urma("urma_0312");

bool Urma0312BondpCreatePsegFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0313", "urma_0314"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0312BondpCreatePsegFunctionFailure::GetName() const
{
    return "bondp_create_pseg 函数故障";
}

std::string Urma0312BondpCreatePsegFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0312BondpCreatePsegFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0312BondpCreatePsegFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0312BondpCreatePsegFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0312BondpCreatePsegFunctionFailure::GetId() const
{
    return "urma_0312";
}
} // namespace diag
