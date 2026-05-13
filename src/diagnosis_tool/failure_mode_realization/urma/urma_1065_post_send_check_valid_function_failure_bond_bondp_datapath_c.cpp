#include "urma_1065_post_send_check_valid_function_failure_bond_bondp_datapath_c.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1065PostSendCheckValidFunctionFailureBondBondpDatapathC> g_urma("urma_1065");

bool Urma1065PostSendCheckValidFunctionFailureBondBondpDatapathC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1066", "urma_1067", "urma_1068"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1065PostSendCheckValidFunctionFailureBondBondpDatapathC::GetName() const
{
    return "post_send_check_valid 函数故障（bond/bondp_datapath.c）";
}

std::string Urma1065PostSendCheckValidFunctionFailureBondBondpDatapathC::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1065PostSendCheckValidFunctionFailureBondBondpDatapathC::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1065PostSendCheckValidFunctionFailureBondBondpDatapathC::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1065PostSendCheckValidFunctionFailureBondBondpDatapathC::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1065PostSendCheckValidFunctionFailureBondBondpDatapathC::GetId() const
{
    return "urma_1065";
}
} // namespace diag
