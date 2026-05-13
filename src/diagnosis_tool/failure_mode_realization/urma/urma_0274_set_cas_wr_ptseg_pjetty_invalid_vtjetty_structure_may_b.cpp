#include "urma_0274_set_cas_wr_ptseg_pjetty_invalid_vtjetty_structure_may_b.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0274SetCasWrPtsegPjettyInvalidVtjettyStructureMayB> g_urma("urma_0274");

bool Urma0274SetCasWrPtsegPjettyInvalidVtjettyStructureMayB::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid vtjetty, the structure may be self-consturcted."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0274SetCasWrPtsegPjettyInvalidVtjettyStructureMayB::GetName() const
{
    return "set_cas_wr_ptseg_pjetty Invalid vtjetty, the structure may b";
}

std::string Urma0274SetCasWrPtsegPjettyInvalidVtjettyStructureMayB::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bdp_tjetty(bdp_tjetty)`；该路径返回 URMA_EINVAL";
}

RootCause Urma0274SetCasWrPtsegPjettyInvalidVtjettyStructureMayB::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0274SetCasWrPtsegPjettyInvalidVtjettyStructureMayB::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0274SetCasWrPtsegPjettyInvalidVtjettyStructureMayB::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid vtjetty, the structure may be self-consturcted.";
}

std::string Urma0274SetCasWrPtsegPjettyInvalidVtjettyStructureMayB::GetId() const
{
    return "urma_0274";
}
} // namespace diag
