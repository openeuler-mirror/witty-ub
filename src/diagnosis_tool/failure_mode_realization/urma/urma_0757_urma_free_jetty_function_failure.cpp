#include "urma_0757_urma_free_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0757UrmaFreeJettyFunctionFailure> g_urma("urma_0757");

bool Urma0757UrmaFreeJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0758", "urma_0759", "urma_0760"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0757UrmaFreeJettyFunctionFailure::GetName() const
{
    return "urma_free_jetty 函数故障";
}

std::string Urma0757UrmaFreeJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0757UrmaFreeJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0757UrmaFreeJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0757UrmaFreeJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0757UrmaFreeJettyFunctionFailure::GetId() const
{
    return "urma_0757";
}
} // namespace diag
