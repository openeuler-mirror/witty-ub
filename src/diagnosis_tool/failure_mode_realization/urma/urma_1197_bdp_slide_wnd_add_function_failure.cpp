#include "urma_1197_bdp_slide_wnd_add_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1197BdpSlideWndAddFunctionFailure> g_urma("urma_1197");

bool Urma1197BdpSlideWndAddFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1198"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1197BdpSlideWndAddFunctionFailure::GetName() const
{
    return "bdp_slide_wnd_add 函数故障";
}

std::string Urma1197BdpSlideWndAddFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1197BdpSlideWndAddFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1197BdpSlideWndAddFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1197BdpSlideWndAddFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1197BdpSlideWndAddFunctionFailure::GetId() const
{
    return "urma_1197";
}
} // namespace diag
