#include "urma_0826_urma_set_jetty_opt_failed_exec_ops_set_jetty_opt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0826UrmaSetJettyOptFailedExecOpsSetJettyOpt> g_urma("urma_0826");

bool Urma0826UrmaSetJettyOptFailedExecOpsSetJettyOpt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec ops->set_jetty_opt."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0826UrmaSetJettyOptFailedExecOpsSetJettyOpt::GetName() const
{
    return "urma_set_jetty_opt Failed to exec ops->set_jetty_opt.";
}

std::string Urma0826UrmaSetJettyOptFailedExecOpsSetJettyOpt::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `status != URMA_SUCCESS`；该路径返回 status";
}

RootCause Urma0826UrmaSetJettyOptFailedExecOpsSetJettyOpt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0826UrmaSetJettyOptFailedExecOpsSetJettyOpt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0826UrmaSetJettyOptFailedExecOpsSetJettyOpt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec ops->set_jetty_opt.";
}

std::string Urma0826UrmaSetJettyOptFailedExecOpsSetJettyOpt::GetId() const
{
    return "urma_0826";
}
} // namespace diag
