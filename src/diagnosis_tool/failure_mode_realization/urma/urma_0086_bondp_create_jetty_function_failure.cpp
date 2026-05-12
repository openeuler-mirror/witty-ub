#include "urma_0086_bondp_create_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0086BondpCreateJettyFunctionFailure> g_urma("urma_0086");

bool Urma0086BondpCreateJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0087", "urma_0088", "urma_0089", "urma_0090", "urma_0091",
                                                    "urma_0092", "urma_0093", "urma_0094", "urma_0095"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0086BondpCreateJettyFunctionFailure::GetName() const
{
    return "bondp_create_jetty 函数故障";
}

std::string Urma0086BondpCreateJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0086BondpCreateJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0086BondpCreateJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0086BondpCreateJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0086BondpCreateJettyFunctionFailure::GetId() const
{
    return "urma_0086";
}
} // namespace diag
