#include "urma_0203_remove_remote_jetty_id_info_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0203RemoveRemoteJettyIdInfoFunctionFailure> g_urma("urma_0203");

bool Urma0203RemoveRemoteJettyIdInfoFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0204"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0203RemoveRemoteJettyIdInfoFunctionFailure::GetName() const
{
    return "remove_remote_jetty_id_info 函数故障";
}

std::string Urma0203RemoveRemoteJettyIdInfoFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0203RemoveRemoteJettyIdInfoFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0203RemoveRemoteJettyIdInfoFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0203RemoveRemoteJettyIdInfoFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0203RemoveRemoteJettyIdInfoFunctionFailure::GetId() const
{
    return "urma_0203";
}
} // namespace diag
