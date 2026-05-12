#include "urma_0243_get_comp_urma_jetty_id_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0243GetCompUrmaJettyIdFunctionFailure> g_urma("urma_0243");

bool Urma0243GetCompUrmaJettyIdFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0244"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0243GetCompUrmaJettyIdFunctionFailure::GetName() const
{
    return "get_comp_urma_jetty_id 函数故障";
}

std::string Urma0243GetCompUrmaJettyIdFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0243GetCompUrmaJettyIdFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0243GetCompUrmaJettyIdFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0243GetCompUrmaJettyIdFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0243GetCompUrmaJettyIdFunctionFailure::GetId() const
{
    return "urma_0243";
}
} // namespace diag
