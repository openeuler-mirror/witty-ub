#include "urma_0251_post_recv_check_valid_function_failure_bond_bondp_datapath_c.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0251PostRecvCheckValidFunctionFailureBondBondpDatapathC> g_urma("urma_0251");

bool Urma0251PostRecvCheckValidFunctionFailureBondBondpDatapathC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0252"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0251PostRecvCheckValidFunctionFailureBondBondpDatapathC::GetName() const
{
    return "post_recv_check_valid 函数故障（bond/bondp_datapath.c）";
}

std::string Urma0251PostRecvCheckValidFunctionFailureBondBondpDatapathC::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0251PostRecvCheckValidFunctionFailureBondBondpDatapathC::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0251PostRecvCheckValidFunctionFailureBondBondpDatapathC::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0251PostRecvCheckValidFunctionFailureBondBondpDatapathC::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0251PostRecvCheckValidFunctionFailureBondBondpDatapathC::GetId() const
{
    return "urma_0251";
}
} // namespace diag
