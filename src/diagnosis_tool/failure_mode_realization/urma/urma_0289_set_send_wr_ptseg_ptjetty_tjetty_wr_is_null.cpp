#include "urma_0289_set_send_wr_ptseg_ptjetty_tjetty_wr_is_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0289SetSendWrPtsegPtjettyTjettyWrIsNull> g_urma("urma_0289");

bool Urma0289SetSendWrPtsegPtjettyTjettyWrIsNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"tjetty in WR is NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0289SetSendWrPtsegPtjettyTjettyWrIsNull::GetName() const
{
    return "set_send_wr_ptseg_ptjetty tjetty in WR is NULL";
}

std::string Urma0289SetSendWrPtsegPtjettyTjettyWrIsNull::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `vtjetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0289SetSendWrPtsegPtjettyTjettyWrIsNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0289SetSendWrPtsegPtjettyTjettyWrIsNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0289SetSendWrPtsegPtjettyTjettyWrIsNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：tjetty in WR is NULL";
}

std::string Urma0289SetSendWrPtsegPtjettyTjettyWrIsNull::GetId() const
{
    return "urma_0289";
}
} // namespace diag
