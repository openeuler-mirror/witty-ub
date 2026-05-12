#include "urma_1057_handle_recv_function_failure_bond_bondp_datapath_c.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1057HandleRecvFunctionFailureBondBondpDatapathC> g_urma("urma_1057");

bool Urma1057HandleRecvFunctionFailureBondBondpDatapathC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1058", "urma_1059"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1057HandleRecvFunctionFailureBondBondpDatapathC::GetName() const
{
    return "handle_recv 函数故障（bond/bondp_datapath.c）";
}

std::string Urma1057HandleRecvFunctionFailureBondBondpDatapathC::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1057HandleRecvFunctionFailureBondBondpDatapathC::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1057HandleRecvFunctionFailureBondBondpDatapathC::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1057HandleRecvFunctionFailureBondBondpDatapathC::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1057HandleRecvFunctionFailureBondBondpDatapathC::GetId() const
{
    return "urma_1057";
}
} // namespace diag
