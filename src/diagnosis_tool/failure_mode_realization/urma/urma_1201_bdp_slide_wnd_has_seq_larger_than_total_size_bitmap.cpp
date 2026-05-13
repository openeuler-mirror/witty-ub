#include "urma_1201_bdp_slide_wnd_has_seq_larger_than_total_size_bitmap.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1201BdpSlideWndHasSeqLargerThanTotalSizeBitmap> g_urma("urma_1201");

bool Urma1201BdpSlideWndHasSeqLargerThanTotalSizeBitmap::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Seq larger than total size of bitmap"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1201BdpSlideWndHasSeqLargerThanTotalSizeBitmap::GetName() const
{
    return "bdp_slide_wnd_has Seq larger than total size of bitmap";
}

std::string Urma1201BdpSlideWndHasSeqLargerThanTotalSizeBitmap::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `seq >= wnd->total_size`；该路径返回 -1";
}

RootCause Urma1201BdpSlideWndHasSeqLargerThanTotalSizeBitmap::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1201BdpSlideWndHasSeqLargerThanTotalSizeBitmap::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1201BdpSlideWndHasSeqLargerThanTotalSizeBitmap::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Seq larger than total size of bitmap";
}

std::string Urma1201BdpSlideWndHasSeqLargerThanTotalSizeBitmap::GetId() const
{
    return "urma_1201";
}
} // namespace diag
