#include "urma_0841_urma_set_jfs_opt_failed_exec_urma_jfr_set_options.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0841UrmaSetJfsOptFailedExecUrmaJfrSetOptions> g_urma("urma_0841");

bool Urma0841UrmaSetJfsOptFailedExecUrmaJfrSetOptions::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec urma_jfr_set_options."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0841UrmaSetJfsOptFailedExecUrmaJfrSetOptions::GetName() const
{
    return "urma_set_jfs_opt Failed to exec urma_jfr_set_options.";
}

std::string Urma0841UrmaSetJfsOptFailedExecUrmaJfrSetOptions::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `status != URMA_SUCCESS`；该路径返回 status";
}

RootCause Urma0841UrmaSetJfsOptFailedExecUrmaJfrSetOptions::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0841UrmaSetJfsOptFailedExecUrmaJfrSetOptions::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0841UrmaSetJfsOptFailedExecUrmaJfrSetOptions::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec urma_jfr_set_options.";
}

std::string Urma0841UrmaSetJfsOptFailedExecUrmaJfrSetOptions::GetId() const
{
    return "urma_0841";
}
} // namespace diag
