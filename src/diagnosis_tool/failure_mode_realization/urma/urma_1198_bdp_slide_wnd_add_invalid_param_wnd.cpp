#include "urma_1198_bdp_slide_wnd_add_invalid_param_wnd.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1198BdpSlideWndAddInvalidParamWnd> g_urma("urma_1198");

bool Urma1198BdpSlideWndAddInvalidParamWnd::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param wnd"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1198BdpSlideWndAddInvalidParamWnd::GetName() const
{
    return "bdp_slide_wnd_add Invalid param wnd";
}

std::string Urma1198BdpSlideWndAddInvalidParamWnd::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `wnd == NULL`；该路径返回 -1";
}

RootCause Urma1198BdpSlideWndAddInvalidParamWnd::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1198BdpSlideWndAddInvalidParamWnd::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1198BdpSlideWndAddInvalidParamWnd::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param wnd";
}

std::string Urma1198BdpSlideWndAddInvalidParamWnd::GetId() const
{
    return "urma_1198";
}
} // namespace diag
