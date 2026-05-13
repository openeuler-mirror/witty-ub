#include "urma_1069_resend_wr_from_node_function_failure_bond_bondp_datapath_c.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1069ResendWrFromNodeFunctionFailureBondBondpDatapathC> g_urma("urma_1069");

bool Urma1069ResendWrFromNodeFunctionFailureBondBondpDatapathC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1070"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1069ResendWrFromNodeFunctionFailureBondBondpDatapathC::GetName() const
{
    return "resend_wr_from_node 函数故障（bond/bondp_datapath.c）";
}

std::string Urma1069ResendWrFromNodeFunctionFailureBondBondpDatapathC::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1069ResendWrFromNodeFunctionFailureBondBondpDatapathC::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1069ResendWrFromNodeFunctionFailureBondBondpDatapathC::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1069ResendWrFromNodeFunctionFailureBondBondpDatapathC::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1069ResendWrFromNodeFunctionFailureBondBondpDatapathC::GetId() const
{
    return "urma_1069";
}
} // namespace diag
