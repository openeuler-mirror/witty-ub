#include "urma_1128_bondp_delete_vseg_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1128BondpDeleteVsegFunctionFailure> g_urma("urma_1128");

bool Urma1128BondpDeleteVsegFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1129", "urma_1130"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1128BondpDeleteVsegFunctionFailure::GetName() const
{
    return "bondp_delete_vseg 函数故障";
}

std::string Urma1128BondpDeleteVsegFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1128BondpDeleteVsegFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1128BondpDeleteVsegFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1128BondpDeleteVsegFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1128BondpDeleteVsegFunctionFailure::GetId() const
{
    return "urma_1128";
}
} // namespace diag
