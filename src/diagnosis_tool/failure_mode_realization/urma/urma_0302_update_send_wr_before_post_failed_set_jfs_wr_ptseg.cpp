#include "urma_0302_update_send_wr_before_post_failed_set_jfs_wr_ptseg.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0302UpdateSendWrBeforePostFailedSetJfsWrPtseg> g_urma("urma_0302");

bool Urma0302UpdateSendWrBeforePostFailedSetJfsWrPtseg::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to set_jfs_wr_ptseg_ptjetty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0302UpdateSendWrBeforePostFailedSetJfsWrPtseg::GetName() const
{
    return "update_send_wr_before_post Failed to set_jfs_wr_ptseg_ptjetty";
}

std::string Urma0302UpdateSendWrBeforePostFailedSetJfsWrPtseg::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret != 0`；该路径返回 ret";
}

RootCause Urma0302UpdateSendWrBeforePostFailedSetJfsWrPtseg::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0302UpdateSendWrBeforePostFailedSetJfsWrPtseg::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0302UpdateSendWrBeforePostFailedSetJfsWrPtseg::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to set_jfs_wr_ptseg_ptjetty";
}

std::string Urma0302UpdateSendWrBeforePostFailedSetJfsWrPtseg::GetId() const
{
    return "urma_0302";
}
} // namespace diag
