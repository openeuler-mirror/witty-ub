#include "urma_0257_post_send_check_valid_function_failure_bond_bondp_datapath_c.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0257PostSendCheckValidFunctionFailureBondBondpDatapathC> g_urma("urma_0257");

bool Urma0257PostSendCheckValidFunctionFailureBondBondpDatapathC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0258", "urma_0259", "urma_0260", "urma_0261"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0257PostSendCheckValidFunctionFailureBondBondpDatapathC::GetName() const
{
    return "post_send_check_valid 函数故障（bond/bondp_datapath.c）";
}

std::string Urma0257PostSendCheckValidFunctionFailureBondBondpDatapathC::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0257PostSendCheckValidFunctionFailureBondBondpDatapathC::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0257PostSendCheckValidFunctionFailureBondBondpDatapathC::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0257PostSendCheckValidFunctionFailureBondBondpDatapathC::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0257PostSendCheckValidFunctionFailureBondBondpDatapathC::GetId() const
{
    return "urma_0257";
}
} // namespace diag
