#include "urma_0413_urma_cmd_delete_jetty_batch_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0413UrmaCmdDeleteJettyBatchFunctionFailure> g_urma("urma_0413");

bool Urma0413UrmaCmdDeleteJettyBatchFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0414", "urma_0415", "urma_0416", "urma_0417",
                                                    "urma_0418", "urma_0419", "urma_0420"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0413UrmaCmdDeleteJettyBatchFunctionFailure::GetName() const
{
    return "urma_cmd_delete_jetty_batch 函数故障";
}

std::string Urma0413UrmaCmdDeleteJettyBatchFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0413UrmaCmdDeleteJettyBatchFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0413UrmaCmdDeleteJettyBatchFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0413UrmaCmdDeleteJettyBatchFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0413UrmaCmdDeleteJettyBatchFunctionFailure::GetId() const
{
    return "urma_0413";
}
} // namespace diag
