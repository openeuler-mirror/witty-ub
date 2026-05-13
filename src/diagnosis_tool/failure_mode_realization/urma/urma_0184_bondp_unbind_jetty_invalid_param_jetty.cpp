#include "urma_0184_bondp_unbind_jetty_invalid_param_jetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0184BondpUnbindJettyInvalidParamJetty> g_urma("urma_0184");

bool Urma0184BondpUnbindJettyInvalidParamJetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param jetty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0184BondpUnbindJettyInvalidParamJetty::GetName() const
{
    return "bondp_unbind_jetty Invalid param jetty";
}

std::string Urma0184BondpUnbindJettyInvalidParamJetty::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bondp_comp(bdp_jetty)`；该路径返回 URMA_EINVAL";
}

RootCause Urma0184BondpUnbindJettyInvalidParamJetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0184BondpUnbindJettyInvalidParamJetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0184BondpUnbindJettyInvalidParamJetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param jetty";
}

std::string Urma0184BondpUnbindJettyInvalidParamJetty::GetId() const
{
    return "urma_0184";
}
} // namespace diag
