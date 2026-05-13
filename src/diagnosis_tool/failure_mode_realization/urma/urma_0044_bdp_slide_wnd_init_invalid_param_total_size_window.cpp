#include "urma_0044_bdp_slide_wnd_init_invalid_param_total_size_window.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0044BdpSlideWndInitInvalidParamTotalSizeWindow> g_urma("urma_0044");

bool Urma0044BdpSlideWndInitInvalidParamTotalSizeWindow::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param: total_size <= window_size"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0044BdpSlideWndInitInvalidParamTotalSizeWindow::GetName() const
{
    return "bdp_slide_wnd_init Invalid param: total_size <= window_";
}

std::string Urma0044BdpSlideWndInitInvalidParamTotalSizeWindow::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `total_size <= window_size`；该路径返回 -1";
}

RootCause Urma0044BdpSlideWndInitInvalidParamTotalSizeWindow::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0044BdpSlideWndInitInvalidParamTotalSizeWindow::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0044BdpSlideWndInitInvalidParamTotalSizeWindow::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param: total_size <= window_size";
}

std::string Urma0044BdpSlideWndInitInvalidParamTotalSizeWindow::GetId() const
{
    return "urma_0044";
}
} // namespace diag
