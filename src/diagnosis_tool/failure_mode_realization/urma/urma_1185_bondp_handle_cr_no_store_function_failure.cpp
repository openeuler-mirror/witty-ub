#include "urma_1185_bondp_handle_cr_no_store_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1185BondpHandleCrNoStoreFunctionFailure> g_urma("urma_1185");

bool Urma1185BondpHandleCrNoStoreFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1186"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1185BondpHandleCrNoStoreFunctionFailure::GetName() const
{
    return "bondp_handle_cr_no_store 函数故障";
}

std::string Urma1185BondpHandleCrNoStoreFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1185BondpHandleCrNoStoreFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1185BondpHandleCrNoStoreFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1185BondpHandleCrNoStoreFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1185BondpHandleCrNoStoreFunctionFailure::GetId() const
{
    return "urma_1185";
}
} // namespace diag
