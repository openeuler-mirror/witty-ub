#include "urma_0083_bondp_bind_jetty_invalid_param_jetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0083BondpBindJettyInvalidParamJetty> g_urma("urma_0083");

bool Urma0083BondpBindJettyInvalidParamJetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param jetty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0083BondpBindJettyInvalidParamJetty::GetName() const
{
    return "bondp_bind_jetty Invalid param jetty";
}

std::string Urma0083BondpBindJettyInvalidParamJetty::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bondp_comp(bdp_jetty)`；该路径返回 URMA_EINVAL";
}

RootCause Urma0083BondpBindJettyInvalidParamJetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0083BondpBindJettyInvalidParamJetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0083BondpBindJettyInvalidParamJetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param jetty";
}

std::string Urma0083BondpBindJettyInvalidParamJetty::GetId() const
{
    return "urma_0083";
}
} // namespace diag
