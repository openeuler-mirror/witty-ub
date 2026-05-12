#include "urma_0652_urma_create_jetty_check_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0652UrmaCreateJettyCheckJfcFunctionFailure> g_urma("urma_0652");

bool Urma0652UrmaCreateJettyCheckJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0653", "urma_0654", "urma_0655"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0652UrmaCreateJettyCheckJfcFunctionFailure::GetName() const
{
    return "urma_create_jetty_check_jfc 函数故障";
}

std::string Urma0652UrmaCreateJettyCheckJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0652UrmaCreateJettyCheckJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0652UrmaCreateJettyCheckJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0652UrmaCreateJettyCheckJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0652UrmaCreateJettyCheckJfcFunctionFailure::GetId() const
{
    return "urma_0652";
}
} // namespace diag
