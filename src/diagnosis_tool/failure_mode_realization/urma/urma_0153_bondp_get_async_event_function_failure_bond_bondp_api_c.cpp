#include "urma_0153_bondp_get_async_event_function_failure_bond_bondp_api_c.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0153BondpGetAsyncEventFunctionFailureBondBondpApiC> g_urma("urma_0153");

bool Urma0153BondpGetAsyncEventFunctionFailureBondBondpApiC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0154"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0153BondpGetAsyncEventFunctionFailureBondBondpApiC::GetName() const
{
    return "bondp_get_async_event 函数故障（bond/bondp_api.c）";
}

std::string Urma0153BondpGetAsyncEventFunctionFailureBondBondpApiC::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0153BondpGetAsyncEventFunctionFailureBondBondpApiC::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0153BondpGetAsyncEventFunctionFailureBondBondpApiC::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0153BondpGetAsyncEventFunctionFailureBondBondpApiC::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0153BondpGetAsyncEventFunctionFailureBondBondpApiC::GetId() const
{
    return "urma_0153";
}
} // namespace diag
