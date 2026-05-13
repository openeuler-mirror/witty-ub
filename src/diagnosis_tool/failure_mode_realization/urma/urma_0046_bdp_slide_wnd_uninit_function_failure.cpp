#include "urma_0046_bdp_slide_wnd_uninit_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0046BdpSlideWndUninitFunctionFailure> g_urma("urma_0046");

bool Urma0046BdpSlideWndUninitFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0047"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0046BdpSlideWndUninitFunctionFailure::GetName() const
{
    return "bdp_slide_wnd_uninit 函数故障";
}

std::string Urma0046BdpSlideWndUninitFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0046BdpSlideWndUninitFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0046BdpSlideWndUninitFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0046BdpSlideWndUninitFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0046BdpSlideWndUninitFunctionFailure::GetId() const
{
    return "urma_0046";
}
} // namespace diag
