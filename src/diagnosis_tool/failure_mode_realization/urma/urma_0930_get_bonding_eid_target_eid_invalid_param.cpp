#include "urma_0930_get_bonding_eid_target_eid_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0930GetBondingEidTargetEidInvalidParam> g_urma("urma_0930");

bool Urma0930GetBondingEidTargetEidInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0930GetBondingEidTargetEidInvalidParam::GetName() const
{
    return "get_bonding_eid_by_target_eid Invalid param";
}

std::string Urma0930GetBondingEidTargetEidInvalidParam::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `topo_map == NULL || target_eid == NULL`；该路径返回 -1";
}

RootCause Urma0930GetBondingEidTargetEidInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0930GetBondingEidTargetEidInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0930GetBondingEidTargetEidInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param";
}

std::string Urma0930GetBondingEidTargetEidInvalidParam::GetId() const
{
    return "urma_0930";
}
} // namespace diag
