#include "urma_0290_set_send_wr_ptseg_ptjetty_invalid_vtjetty_structure_may_b.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0290SetSendWrPtsegPtjettyInvalidVtjettyStructureMayB> g_urma("urma_0290");

bool Urma0290SetSendWrPtsegPtjettyInvalidVtjettyStructureMayB::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid vtjetty, the structure may be self-consturcted."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0290SetSendWrPtsegPtjettyInvalidVtjettyStructureMayB::GetName() const
{
    return "set_send_wr_ptseg_ptjetty Invalid vtjetty, the structure may b";
}

std::string Urma0290SetSendWrPtsegPtjettyInvalidVtjettyStructureMayB::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bdp_tjetty(bdp_tjetty)`；该路径返回 URMA_EINVAL";
}

RootCause Urma0290SetSendWrPtsegPtjettyInvalidVtjettyStructureMayB::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0290SetSendWrPtsegPtjettyInvalidVtjettyStructureMayB::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0290SetSendWrPtsegPtjettyInvalidVtjettyStructureMayB::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid vtjetty, the structure may be self-consturcted.";
}

std::string Urma0290SetSendWrPtsegPtjettyInvalidVtjettyStructureMayB::GetId() const
{
    return "urma_0290";
}
} // namespace diag
