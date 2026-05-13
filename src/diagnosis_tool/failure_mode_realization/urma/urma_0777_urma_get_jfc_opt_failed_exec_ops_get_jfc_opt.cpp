#include "urma_0777_urma_get_jfc_opt_failed_exec_ops_get_jfc_opt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0777UrmaGetJfcOptFailedExecOpsGetJfcOpt> g_urma("urma_0777");

bool Urma0777UrmaGetJfcOptFailedExecOpsGetJfcOpt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec ops->get_jfc_opt."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0777UrmaGetJfcOptFailedExecOpsGetJfcOpt::GetName() const
{
    return "urma_get_jfc_opt Failed to exec ops->get_jfc_opt.";
}

std::string Urma0777UrmaGetJfcOptFailedExecOpsGetJfcOpt::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `status != URMA_SUCCESS`；该路径返回 status";
}

RootCause Urma0777UrmaGetJfcOptFailedExecOpsGetJfcOpt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0777UrmaGetJfcOptFailedExecOpsGetJfcOpt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0777UrmaGetJfcOptFailedExecOpsGetJfcOpt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec ops->get_jfc_opt.";
}

std::string Urma0777UrmaGetJfcOptFailedExecOpsGetJfcOpt::GetId() const
{
    return "urma_0777";
}
} // namespace diag
