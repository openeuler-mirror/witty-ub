#include "urma_0832_urma_set_jfc_opt_failed_exec_urma_jfc_set_options.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0832UrmaSetJfcOptFailedExecUrmaJfcSetOptions> g_urma("urma_0832");

bool Urma0832UrmaSetJfcOptFailedExecUrmaJfcSetOptions::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec urma_jfc_set_options."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0832UrmaSetJfcOptFailedExecUrmaJfcSetOptions::GetName() const
{
    return "urma_set_jfc_opt Failed to exec urma_jfc_set_options.";
}

std::string Urma0832UrmaSetJfcOptFailedExecUrmaJfcSetOptions::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `status != URMA_SUCCESS`；该路径返回 status";
}

RootCause Urma0832UrmaSetJfcOptFailedExecUrmaJfcSetOptions::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0832UrmaSetJfcOptFailedExecUrmaJfcSetOptions::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0832UrmaSetJfcOptFailedExecUrmaJfcSetOptions::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec urma_jfc_set_options.";
}

std::string Urma0832UrmaSetJfcOptFailedExecUrmaJfcSetOptions::GetId() const
{
    return "urma_0832";
}
} // namespace diag
