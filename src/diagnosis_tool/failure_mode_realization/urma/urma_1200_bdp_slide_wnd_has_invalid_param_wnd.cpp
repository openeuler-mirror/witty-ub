#include "urma_1200_bdp_slide_wnd_has_invalid_param_wnd.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1200BdpSlideWndHasInvalidParamWnd> g_urma("urma_1200");

bool Urma1200BdpSlideWndHasInvalidParamWnd::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param wnd"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1200BdpSlideWndHasInvalidParamWnd::GetName() const
{
    return "bdp_slide_wnd_has Invalid param wnd";
}

std::string Urma1200BdpSlideWndHasInvalidParamWnd::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `wnd == NULL`；该路径返回 -1";
}

RootCause Urma1200BdpSlideWndHasInvalidParamWnd::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1200BdpSlideWndHasInvalidParamWnd::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1200BdpSlideWndHasInvalidParamWnd::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param wnd";
}

std::string Urma1200BdpSlideWndHasInvalidParamWnd::GetId() const
{
    return "urma_1200";
}
} // namespace diag
