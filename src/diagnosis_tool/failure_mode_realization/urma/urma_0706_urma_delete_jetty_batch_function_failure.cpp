#include "urma_0706_urma_delete_jetty_batch_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0706UrmaDeleteJettyBatchFunctionFailure> g_urma("urma_0706");

bool Urma0706UrmaDeleteJettyBatchFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0707", "urma_0708", "urma_0709",
                                                    "urma_0710", "urma_0711", "urma_0712"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0706UrmaDeleteJettyBatchFunctionFailure::GetName() const
{
    return "urma_delete_jetty_batch 函数故障";
}

std::string Urma0706UrmaDeleteJettyBatchFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0706UrmaDeleteJettyBatchFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0706UrmaDeleteJettyBatchFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0706UrmaDeleteJettyBatchFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0706UrmaDeleteJettyBatchFunctionFailure::GetId() const
{
    return "urma_0706";
}
} // namespace diag
