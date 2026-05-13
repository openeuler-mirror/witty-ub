#include "urma_1055_bondp_post_send_wr_no_store_function_failure_bond_bondp.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1055BondpPostSendWrNoStoreFunctionFailureBondBondp> g_urma("urma_1055");

bool Urma1055BondpPostSendWrNoStoreFunctionFailureBondBondp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1056"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1055BondpPostSendWrNoStoreFunctionFailureBondBondp::GetName() const
{
    return "bondp_post_send_wr_no_store 函数故障（bond/bondp_datapath.c）";
}

std::string Urma1055BondpPostSendWrNoStoreFunctionFailureBondBondp::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1055BondpPostSendWrNoStoreFunctionFailureBondBondp::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1055BondpPostSendWrNoStoreFunctionFailureBondBondp::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1055BondpPostSendWrNoStoreFunctionFailureBondBondp::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1055BondpPostSendWrNoStoreFunctionFailureBondBondp::GetId() const
{
    return "urma_1055";
}
} // namespace diag
