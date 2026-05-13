#include "urma_0874_urma_post_jetty_recv_wr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0874UrmaPostJettyRecvWrFunctionFailure> g_urma("urma_0874");

bool Urma0874UrmaPostJettyRecvWrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0875"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0874UrmaPostJettyRecvWrFunctionFailure::GetName() const
{
    return "urma_post_jetty_recv_wr 函数故障";
}

std::string Urma0874UrmaPostJettyRecvWrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0874UrmaPostJettyRecvWrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0874UrmaPostJettyRecvWrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0874UrmaPostJettyRecvWrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0874UrmaPostJettyRecvWrFunctionFailure::GetId() const
{
    return "urma_0874";
}
} // namespace diag
