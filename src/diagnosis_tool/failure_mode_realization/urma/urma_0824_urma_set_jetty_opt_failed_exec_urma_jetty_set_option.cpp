#include "urma_0824_urma_set_jetty_opt_failed_exec_urma_jetty_set_option.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0824UrmaSetJettyOptFailedExecUrmaJettySetOption> g_urma("urma_0824");

bool Urma0824UrmaSetJettyOptFailedExecUrmaJettySetOption::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec urma_jetty_set_options."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0824UrmaSetJettyOptFailedExecUrmaJettySetOption::GetName() const
{
    return "urma_set_jetty_opt Failed to exec urma_jetty_set_option";
}

std::string Urma0824UrmaSetJettyOptFailedExecUrmaJettySetOption::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `status != URMA_SUCCESS`；该路径返回 status";
}

RootCause Urma0824UrmaSetJettyOptFailedExecUrmaJettySetOption::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0824UrmaSetJettyOptFailedExecUrmaJettySetOption::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0824UrmaSetJettyOptFailedExecUrmaJettySetOption::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec urma_jetty_set_options.";
}

std::string Urma0824UrmaSetJettyOptFailedExecUrmaJettySetOption::GetId() const
{
    return "urma_0824";
}
} // namespace diag
