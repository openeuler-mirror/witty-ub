#include "urma_0656_urma_create_jetty_check_trans_mode_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0656UrmaCreateJettyCheckTransModeFunctionFailure> g_urma("urma_0656");

bool Urma0656UrmaCreateJettyCheckTransModeFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0657", "urma_0658", "urma_0659", "urma_0660", "urma_0661"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0656UrmaCreateJettyCheckTransModeFunctionFailure::GetName() const
{
    return "urma_create_jetty_check_trans_mode 函数故障";
}

std::string Urma0656UrmaCreateJettyCheckTransModeFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0656UrmaCreateJettyCheckTransModeFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0656UrmaCreateJettyCheckTransModeFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0656UrmaCreateJettyCheckTransModeFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0656UrmaCreateJettyCheckTransModeFunctionFailure::GetId() const
{
    return "urma_0656";
}
} // namespace diag
