#include "urma_1203_bdp_slide_wnd_seq_window_invalid_param_wnd.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1203BdpSlideWndSeqWindowInvalidParamWnd> g_urma("urma_1203");

bool Urma1203BdpSlideWndSeqWindowInvalidParamWnd::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param wnd"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1203BdpSlideWndSeqWindowInvalidParamWnd::GetName() const
{
    return "bdp_slide_wnd_seq_in_window Invalid param wnd";
}

std::string Urma1203BdpSlideWndSeqWindowInvalidParamWnd::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `wnd == NULL`；该路径返回 false";
}

RootCause Urma1203BdpSlideWndSeqWindowInvalidParamWnd::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1203BdpSlideWndSeqWindowInvalidParamWnd::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1203BdpSlideWndSeqWindowInvalidParamWnd::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param wnd";
}

std::string Urma1203BdpSlideWndSeqWindowInvalidParamWnd::GetId() const
{
    return "urma_1203";
}
} // namespace diag
