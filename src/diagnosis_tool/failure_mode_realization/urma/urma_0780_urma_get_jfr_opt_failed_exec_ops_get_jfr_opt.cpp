#include "urma_0780_urma_get_jfr_opt_failed_exec_ops_get_jfr_opt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0780UrmaGetJfrOptFailedExecOpsGetJfrOpt> g_urma("urma_0780");

bool Urma0780UrmaGetJfrOptFailedExecOpsGetJfrOpt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec ops->get_jfr_opt."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0780UrmaGetJfrOptFailedExecOpsGetJfrOpt::GetName() const
{
    return "urma_get_jfr_opt Failed to exec ops->get_jfr_opt.";
}

std::string Urma0780UrmaGetJfrOptFailedExecOpsGetJfrOpt::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `status != URMA_SUCCESS`；该路径返回 status";
}

RootCause Urma0780UrmaGetJfrOptFailedExecOpsGetJfrOpt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0780UrmaGetJfrOptFailedExecOpsGetJfrOpt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0780UrmaGetJfrOptFailedExecOpsGetJfrOpt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec ops->get_jfr_opt.";
}

std::string Urma0780UrmaGetJfrOptFailedExecOpsGetJfrOpt::GetId() const
{
    return "urma_0780";
}
} // namespace diag
