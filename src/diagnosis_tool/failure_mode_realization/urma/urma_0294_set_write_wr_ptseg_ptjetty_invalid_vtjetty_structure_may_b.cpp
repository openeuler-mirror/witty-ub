#include "urma_0294_set_write_wr_ptseg_ptjetty_invalid_vtjetty_structure_may_b.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0294SetWriteWrPtsegPtjettyInvalidVtjettyStructureMayB> g_urma("urma_0294");

bool Urma0294SetWriteWrPtsegPtjettyInvalidVtjettyStructureMayB::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid vtjetty, the structure may be self-consturcted."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0294SetWriteWrPtsegPtjettyInvalidVtjettyStructureMayB::GetName() const
{
    return "set_write_wr_ptseg_ptjetty Invalid vtjetty, the structure may b";
}

std::string Urma0294SetWriteWrPtsegPtjettyInvalidVtjettyStructureMayB::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bdp_tjetty(bdp_tjetty)`；该路径返回 URMA_EINVAL";
}

RootCause Urma0294SetWriteWrPtsegPtjettyInvalidVtjettyStructureMayB::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0294SetWriteWrPtsegPtjettyInvalidVtjettyStructureMayB::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0294SetWriteWrPtsegPtjettyInvalidVtjettyStructureMayB::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid vtjetty, the structure may be self-consturcted.";
}

std::string Urma0294SetWriteWrPtsegPtjettyInvalidVtjettyStructureMayB::GetId() const
{
    return "urma_0294";
}
} // namespace diag
