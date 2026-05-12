#include "urma_0774_urma_get_jetty_opt_failed_exec_ops_get_jetty_opt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0774UrmaGetJettyOptFailedExecOpsGetJettyOpt> g_urma("urma_0774");

bool Urma0774UrmaGetJettyOptFailedExecOpsGetJettyOpt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec ops->get_jetty_opt."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0774UrmaGetJettyOptFailedExecOpsGetJettyOpt::GetName() const
{
    return "urma_get_jetty_opt Failed to exec ops->get_jetty_opt.";
}

std::string Urma0774UrmaGetJettyOptFailedExecOpsGetJettyOpt::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `status != URMA_SUCCESS`；该路径返回 status";
}

RootCause Urma0774UrmaGetJettyOptFailedExecOpsGetJettyOpt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0774UrmaGetJettyOptFailedExecOpsGetJettyOpt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0774UrmaGetJettyOptFailedExecOpsGetJettyOpt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec ops->get_jetty_opt.";
}

std::string Urma0774UrmaGetJettyOptFailedExecOpsGetJettyOpt::GetId() const
{
    return "urma_0774";
}
} // namespace diag
