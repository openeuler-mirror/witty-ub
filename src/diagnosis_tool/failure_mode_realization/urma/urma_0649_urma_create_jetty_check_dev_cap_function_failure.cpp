#include "urma_0649_urma_create_jetty_check_dev_cap_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0649UrmaCreateJettyCheckDevCapFunctionFailure> g_urma("urma_0649");

bool Urma0649UrmaCreateJettyCheckDevCapFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0650", "urma_0651"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0649UrmaCreateJettyCheckDevCapFunctionFailure::GetName() const
{
    return "urma_create_jetty_check_dev_cap 函数故障";
}

std::string Urma0649UrmaCreateJettyCheckDevCapFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0649UrmaCreateJettyCheckDevCapFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0649UrmaCreateJettyCheckDevCapFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0649UrmaCreateJettyCheckDevCapFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0649UrmaCreateJettyCheckDevCapFunctionFailure::GetId() const
{
    return "urma_0649";
}
} // namespace diag
