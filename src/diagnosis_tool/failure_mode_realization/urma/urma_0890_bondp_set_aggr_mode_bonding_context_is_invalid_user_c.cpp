#include "urma_0890_bondp_set_aggr_mode_bonding_context_is_invalid_user_c.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0890BondpSetAggrModeBondingContextIsInvalidUserC> g_urma("urma_0890");

bool Urma0890BondpSetAggrModeBondingContextIsInvalidUserC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"bonding context is invalid in user ctl"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0890BondpSetAggrModeBondingContextIsInvalidUserC::GetName() const
{
    return "bondp_set_aggr_mode bonding context is invalid in user c";
}

std::string Urma0890BondpSetAggrModeBondingContextIsInvalidUserC::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_ctx(bond_ctx)`；该路径返回 -1";
}

RootCause Urma0890BondpSetAggrModeBondingContextIsInvalidUserC::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0890BondpSetAggrModeBondingContextIsInvalidUserC::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0890BondpSetAggrModeBondingContextIsInvalidUserC::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：bonding context is invalid in user ctl";
}

std::string Urma0890BondpSetAggrModeBondingContextIsInvalidUserC::GetId() const
{
    return "urma_0890";
}
} // namespace diag
