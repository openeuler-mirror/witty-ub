#include "urma_0831_urma_set_jfc_opt_failed_exec_ops_set_jfc_opt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0831UrmaSetJfcOptFailedExecOpsSetJfcOpt> g_urma("urma_0831");

bool Urma0831UrmaSetJfcOptFailedExecOpsSetJfcOpt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec ops->set_jfc_opt."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0831UrmaSetJfcOptFailedExecOpsSetJfcOpt::GetName() const
{
    return "urma_set_jfc_opt Failed to exec ops->set_jfc_opt.";
}

std::string Urma0831UrmaSetJfcOptFailedExecOpsSetJfcOpt::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `status != URMA_SUCCESS`；该路径返回 status";
}

RootCause Urma0831UrmaSetJfcOptFailedExecOpsSetJfcOpt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0831UrmaSetJfcOptFailedExecOpsSetJfcOpt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0831UrmaSetJfcOptFailedExecOpsSetJfcOpt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec ops->set_jfc_opt.";
}

std::string Urma0831UrmaSetJfcOptFailedExecOpsSetJfcOpt::GetId() const
{
    return "urma_0831";
}
} // namespace diag
