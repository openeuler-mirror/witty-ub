#include "urma_0215_bondp_jetty_get_args_list_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0215BondpJettyGetArgsListFunctionFailure> g_urma("urma_0215");

bool Urma0215BondpJettyGetArgsListFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0216", "urma_0217"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0215BondpJettyGetArgsListFunctionFailure::GetName() const
{
    return "bondp_jetty_get_args_list 函数故障";
}

std::string Urma0215BondpJettyGetArgsListFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0215BondpJettyGetArgsListFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0215BondpJettyGetArgsListFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0215BondpJettyGetArgsListFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0215BondpJettyGetArgsListFunctionFailure::GetId() const
{
    return "urma_0215";
}
} // namespace diag
