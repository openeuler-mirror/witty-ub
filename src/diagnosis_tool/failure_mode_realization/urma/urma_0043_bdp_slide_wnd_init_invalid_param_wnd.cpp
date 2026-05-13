#include "urma_0043_bdp_slide_wnd_init_invalid_param_wnd.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0043BdpSlideWndInitInvalidParamWnd> g_urma("urma_0043");

bool Urma0043BdpSlideWndInitInvalidParamWnd::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param wnd"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0043BdpSlideWndInitInvalidParamWnd::GetName() const
{
    return "bdp_slide_wnd_init Invalid param wnd";
}

std::string Urma0043BdpSlideWndInitInvalidParamWnd::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `wnd == NULL`；该路径返回 -1";
}

RootCause Urma0043BdpSlideWndInitInvalidParamWnd::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0043BdpSlideWndInitInvalidParamWnd::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0043BdpSlideWndInitInvalidParamWnd::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param wnd";
}

std::string Urma0043BdpSlideWndInitInvalidParamWnd::GetId() const
{
    return "urma_0043";
}
} // namespace diag
