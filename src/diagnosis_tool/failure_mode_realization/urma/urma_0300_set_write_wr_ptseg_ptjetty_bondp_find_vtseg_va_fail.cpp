#include "urma_0300_set_write_wr_ptseg_ptjetty_bondp_find_vtseg_va_fail.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0300SetWriteWrPtsegPtjettyBondpFindVtsegVaFail> g_urma("urma_0300");

bool Urma0300SetWriteWrPtsegPtjettyBondpFindVtsegVaFail::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"bondp_find_vtseg_by_va fail."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0300SetWriteWrPtsegPtjettyBondpFindVtsegVaFail::GetName() const
{
    return "set_write_wr_ptseg_ptjetty bondp_find_vtseg_by_va fail.（vtseg == NULL）";
}

std::string Urma0300SetWriteWrPtsegPtjettyBondpFindVtsegVaFail::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `vtseg == NULL`；该路径返回 URMA_FAIL";
}

RootCause Urma0300SetWriteWrPtsegPtjettyBondpFindVtsegVaFail::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0300SetWriteWrPtsegPtjettyBondpFindVtsegVaFail::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0300SetWriteWrPtsegPtjettyBondpFindVtsegVaFail::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：bondp_find_vtseg_by_va fail.";
}

std::string Urma0300SetWriteWrPtsegPtjettyBondpFindVtsegVaFail::GetId() const
{
    return "urma_0300";
}
} // namespace diag
