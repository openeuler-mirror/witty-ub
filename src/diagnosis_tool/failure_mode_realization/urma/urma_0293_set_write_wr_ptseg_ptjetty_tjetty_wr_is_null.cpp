#include "urma_0293_set_write_wr_ptseg_ptjetty_tjetty_wr_is_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0293SetWriteWrPtsegPtjettyTjettyWrIsNull> g_urma("urma_0293");

bool Urma0293SetWriteWrPtsegPtjettyTjettyWrIsNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"tjetty in WR is NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0293SetWriteWrPtsegPtjettyTjettyWrIsNull::GetName() const
{
    return "set_write_wr_ptseg_ptjetty tjetty in WR is NULL";
}

std::string Urma0293SetWriteWrPtsegPtjettyTjettyWrIsNull::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `vtjetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0293SetWriteWrPtsegPtjettyTjettyWrIsNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0293SetWriteWrPtsegPtjettyTjettyWrIsNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0293SetWriteWrPtsegPtjettyTjettyWrIsNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：tjetty in WR is NULL";
}

std::string Urma0293SetWriteWrPtsegPtjettyTjettyWrIsNull::GetId() const
{
    return "urma_0293";
}
} // namespace diag
