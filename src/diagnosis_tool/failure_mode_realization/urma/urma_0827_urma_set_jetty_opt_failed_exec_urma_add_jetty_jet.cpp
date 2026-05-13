#include "urma_0827_urma_set_jetty_opt_failed_exec_urma_add_jetty_jet.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0827UrmaSetJettyOptFailedExecUrmaAddJettyJet> g_urma("urma_0827");

bool Urma0827UrmaSetJettyOptFailedExecUrmaAddJettyJet::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec urma_add_jetty_to_jetty_grp."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0827UrmaSetJettyOptFailedExecUrmaAddJettyJet::GetName() const
{
    return "urma_set_jetty_opt Failed to exec urma_add_jetty_to_jet";
}

std::string Urma0827UrmaSetJettyOptFailedExecUrmaAddJettyJet::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret != 0`；该路径返回 URMA_FAIL";
}

RootCause Urma0827UrmaSetJettyOptFailedExecUrmaAddJettyJet::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0827UrmaSetJettyOptFailedExecUrmaAddJettyJet::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0827UrmaSetJettyOptFailedExecUrmaAddJettyJet::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec urma_add_jetty_to_jetty_grp.";
}

std::string Urma0827UrmaSetJettyOptFailedExecUrmaAddJettyJet::GetId() const
{
    return "urma_0827";
}
} // namespace diag
