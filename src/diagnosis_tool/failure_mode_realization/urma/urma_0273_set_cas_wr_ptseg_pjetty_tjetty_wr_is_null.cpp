#include "urma_0273_set_cas_wr_ptseg_pjetty_tjetty_wr_is_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0273SetCasWrPtsegPjettyTjettyWrIsNull> g_urma("urma_0273");

bool Urma0273SetCasWrPtsegPjettyTjettyWrIsNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"tjetty in WR is NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0273SetCasWrPtsegPjettyTjettyWrIsNull::GetName() const
{
    return "set_cas_wr_ptseg_pjetty tjetty in WR is NULL";
}

std::string Urma0273SetCasWrPtsegPjettyTjettyWrIsNull::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `vtjetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0273SetCasWrPtsegPjettyTjettyWrIsNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0273SetCasWrPtsegPjettyTjettyWrIsNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0273SetCasWrPtsegPjettyTjettyWrIsNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：tjetty in WR is NULL";
}

std::string Urma0273SetCasWrPtsegPjettyTjettyWrIsNull::GetId() const
{
    return "urma_0273";
}
} // namespace diag
