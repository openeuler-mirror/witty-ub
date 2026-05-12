#include "urma_1204_bdp_slide_wnd_seq_window_seq_larger_than_total_size.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1204BdpSlideWndSeqWindowSeqLargerThanTotalSize> g_urma("urma_1204");

bool Urma1204BdpSlideWndSeqWindowSeqLargerThanTotalSize::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Seq larger than total size of bitmap"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1204BdpSlideWndSeqWindowSeqLargerThanTotalSize::GetName() const
{
    return "bdp_slide_wnd_seq_in_window Seq larger than total size of bitmap";
}

std::string Urma1204BdpSlideWndSeqWindowSeqLargerThanTotalSize::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `seq >= wnd->total_size`；该路径返回 -1";
}

RootCause Urma1204BdpSlideWndSeqWindowSeqLargerThanTotalSize::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1204BdpSlideWndSeqWindowSeqLargerThanTotalSize::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1204BdpSlideWndSeqWindowSeqLargerThanTotalSize::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Seq larger than total size of bitmap";
}

std::string Urma1204BdpSlideWndSeqWindowSeqLargerThanTotalSize::GetId() const
{
    return "urma_1204";
}
} // namespace diag
