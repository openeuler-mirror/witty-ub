#include "urma_1126_bondp_delete_pseg_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1126BondpDeletePsegFunctionFailure> g_urma("urma_1126");

bool Urma1126BondpDeletePsegFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1127"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1126BondpDeletePsegFunctionFailure::GetName() const
{
    return "bondp_delete_pseg 函数故障";
}

std::string Urma1126BondpDeletePsegFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1126BondpDeletePsegFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1126BondpDeletePsegFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1126BondpDeletePsegFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1126BondpDeletePsegFunctionFailure::GetId() const
{
    return "urma_1126";
}
} // namespace diag
