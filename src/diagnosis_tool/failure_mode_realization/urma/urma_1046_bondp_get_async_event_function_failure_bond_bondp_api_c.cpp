#include "urma_1046_bondp_get_async_event_function_failure_bond_bondp_api_c.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1046BondpGetAsyncEventFunctionFailureBondBondpApiC> g_urma("urma_1046");

bool Urma1046BondpGetAsyncEventFunctionFailureBondBondpApiC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1047", "urma_1048", "urma_1049"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1046BondpGetAsyncEventFunctionFailureBondBondpApiC::GetName() const
{
    return "bondp_get_async_event 函数故障（bond/bondp_api.c）";
}

std::string Urma1046BondpGetAsyncEventFunctionFailureBondBondpApiC::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1046BondpGetAsyncEventFunctionFailureBondBondpApiC::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1046BondpGetAsyncEventFunctionFailureBondBondpApiC::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1046BondpGetAsyncEventFunctionFailureBondBondpApiC::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1046BondpGetAsyncEventFunctionFailureBondBondpApiC::GetId() const
{
    return "urma_1046";
}
} // namespace diag
