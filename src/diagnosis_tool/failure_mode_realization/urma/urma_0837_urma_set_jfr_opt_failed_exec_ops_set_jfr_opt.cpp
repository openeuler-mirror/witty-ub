#include "urma_0837_urma_set_jfr_opt_failed_exec_ops_set_jfr_opt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0837UrmaSetJfrOptFailedExecOpsSetJfrOpt> g_urma("urma_0837");

bool Urma0837UrmaSetJfrOptFailedExecOpsSetJfrOpt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec ops->set_jfr_opt."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0837UrmaSetJfrOptFailedExecOpsSetJfrOpt::GetName() const
{
    return "urma_set_jfr_opt Failed to exec ops->set_jfr_opt.";
}

std::string Urma0837UrmaSetJfrOptFailedExecOpsSetJfrOpt::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `status != URMA_SUCCESS`；该路径返回 status";
}

RootCause Urma0837UrmaSetJfrOptFailedExecOpsSetJfrOpt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0837UrmaSetJfrOptFailedExecOpsSetJfrOpt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0837UrmaSetJfrOptFailedExecOpsSetJfrOpt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec ops->set_jfr_opt.";
}

std::string Urma0837UrmaSetJfrOptFailedExecOpsSetJfrOpt::GetId() const
{
    return "urma_0837";
}
} // namespace diag
