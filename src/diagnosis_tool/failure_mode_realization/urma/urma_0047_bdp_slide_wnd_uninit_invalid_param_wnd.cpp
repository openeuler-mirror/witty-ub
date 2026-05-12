#include "urma_0047_bdp_slide_wnd_uninit_invalid_param_wnd.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0047BdpSlideWndUninitInvalidParamWnd> g_urma("urma_0047");

bool Urma0047BdpSlideWndUninitInvalidParamWnd::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param wnd"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0047BdpSlideWndUninitInvalidParamWnd::GetName() const
{
    return "bdp_slide_wnd_uninit Invalid param wnd";
}

std::string Urma0047BdpSlideWndUninitInvalidParamWnd::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `wnd == NULL`";
}

RootCause Urma0047BdpSlideWndUninitInvalidParamWnd::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0047BdpSlideWndUninitInvalidParamWnd::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0047BdpSlideWndUninitInvalidParamWnd::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param wnd";
}

std::string Urma0047BdpSlideWndUninitInvalidParamWnd::GetId() const
{
    return "urma_0047";
}
} // namespace diag
