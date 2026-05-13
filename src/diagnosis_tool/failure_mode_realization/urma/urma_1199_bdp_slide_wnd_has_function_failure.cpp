#include "urma_1199_bdp_slide_wnd_has_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1199BdpSlideWndHasFunctionFailure> g_urma("urma_1199");

bool Urma1199BdpSlideWndHasFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1200", "urma_1201"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1199BdpSlideWndHasFunctionFailure::GetName() const
{
    return "bdp_slide_wnd_has 函数故障";
}

std::string Urma1199BdpSlideWndHasFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1199BdpSlideWndHasFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1199BdpSlideWndHasFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1199BdpSlideWndHasFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1199BdpSlideWndHasFunctionFailure::GetId() const
{
    return "urma_1199";
}
} // namespace diag
