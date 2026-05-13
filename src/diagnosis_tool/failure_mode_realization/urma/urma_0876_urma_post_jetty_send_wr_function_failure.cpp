#include "urma_0876_urma_post_jetty_send_wr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0876UrmaPostJettySendWrFunctionFailure> g_urma("urma_0876");

bool Urma0876UrmaPostJettySendWrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0877"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0876UrmaPostJettySendWrFunctionFailure::GetName() const
{
    return "urma_post_jetty_send_wr 函数故障";
}

std::string Urma0876UrmaPostJettySendWrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0876UrmaPostJettySendWrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0876UrmaPostJettySendWrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0876UrmaPostJettySendWrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0876UrmaPostJettySendWrFunctionFailure::GetId() const
{
    return "urma_0876";
}
} // namespace diag
