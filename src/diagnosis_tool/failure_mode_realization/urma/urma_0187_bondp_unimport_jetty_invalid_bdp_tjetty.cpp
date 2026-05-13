#include "urma_0187_bondp_unimport_jetty_invalid_bdp_tjetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0187BondpUnimportJettyInvalidBdpTjetty> g_urma("urma_0187");

bool Urma0187BondpUnimportJettyInvalidBdpTjetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid bdp tjetty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0187BondpUnimportJettyInvalidBdpTjetty::GetName() const
{
    return "bondp_unimport_jetty Invalid bdp tjetty";
}

std::string Urma0187BondpUnimportJettyInvalidBdpTjetty::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bdp_tjetty(bdp_tjetty)`；该路径返回 URMA_EINVAL";
}

RootCause Urma0187BondpUnimportJettyInvalidBdpTjetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0187BondpUnimportJettyInvalidBdpTjetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0187BondpUnimportJettyInvalidBdpTjetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid bdp tjetty";
}

std::string Urma0187BondpUnimportJettyInvalidBdpTjetty::GetId() const
{
    return "urma_0187";
}
} // namespace diag
