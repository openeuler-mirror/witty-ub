#include "urma_0279_set_fadd_wr_ptseg_pjetty_tjetty_wr_is_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0279SetFaddWrPtsegPjettyTjettyWrIsNull> g_urma("urma_0279");

bool Urma0279SetFaddWrPtsegPjettyTjettyWrIsNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"tjetty in WR is NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0279SetFaddWrPtsegPjettyTjettyWrIsNull::GetName() const
{
    return "set_fadd_wr_ptseg_pjetty tjetty in WR is NULL";
}

std::string Urma0279SetFaddWrPtsegPjettyTjettyWrIsNull::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `vtjetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0279SetFaddWrPtsegPjettyTjettyWrIsNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0279SetFaddWrPtsegPjettyTjettyWrIsNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0279SetFaddWrPtsegPjettyTjettyWrIsNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：tjetty in WR is NULL";
}

std::string Urma0279SetFaddWrPtsegPjettyTjettyWrIsNull::GetId() const
{
    return "urma_0279";
}
} // namespace diag
