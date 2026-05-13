#include "urma_0045_bdp_slide_wnd_init_failed_init_bitmap.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0045BdpSlideWndInitFailedInitBitmap> g_urma("urma_0045");

bool Urma0045BdpSlideWndInitFailedInitBitmap::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to init bitmap"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0045BdpSlideWndInitFailedInitBitmap::GetName() const
{
    return "bdp_slide_wnd_init Failed to init bitmap";
}

std::string Urma0045BdpSlideWndInitFailedInitBitmap::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `wnd->bits == NULL`；该路径返回 -1";
}

RootCause Urma0045BdpSlideWndInitFailedInitBitmap::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0045BdpSlideWndInitFailedInitBitmap::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0045BdpSlideWndInitFailedInitBitmap::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to init bitmap";
}

std::string Urma0045BdpSlideWndInitFailedInitBitmap::GetId() const
{
    return "urma_0045";
}
} // namespace diag
