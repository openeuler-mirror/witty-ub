#include "urma_0085_bondp_bind_jetty_is_multipath_attributes_jetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0085BondpBindJettyIsMultipathAttributesJetty> g_urma("urma_0085");

bool Urma0085BondpBindJettyIsMultipathAttributesJetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"The is_multipath attributes of jetty and tjetty are different"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0085BondpBindJettyIsMultipathAttributesJetty::GetName() const
{
    return "bondp_bind_jetty The is_multipath attributes of jetty";
}

std::string Urma0085BondpBindJettyIsMultipathAttributesJetty::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `is_in_matrix_server(bdp_jetty->bondp_ctx) && bdp_jetty->is_multipath != "
           "bdp_tjetty->is_multipath`；该路径返回 URMA_EINVAL";
}

RootCause Urma0085BondpBindJettyIsMultipathAttributesJetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0085BondpBindJettyIsMultipathAttributesJetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0085BondpBindJettyIsMultipathAttributesJetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：The is_multipath attributes of jetty and tjetty are different";
}

std::string Urma0085BondpBindJettyIsMultipathAttributesJetty::GetId() const
{
    return "urma_0085";
}
} // namespace diag
