#include "urma_0315_bondp_create_vseg_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0315BondpCreateVsegFunctionFailure> g_urma("urma_0315");

bool Urma0315BondpCreateVsegFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0316"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0315BondpCreateVsegFunctionFailure::GetName() const
{
    return "bondp_create_vseg 函数故障";
}

std::string Urma0315BondpCreateVsegFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0315BondpCreateVsegFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0315BondpCreateVsegFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0315BondpCreateVsegFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0315BondpCreateVsegFunctionFailure::GetId() const
{
    return "urma_0315";
}
} // namespace diag
