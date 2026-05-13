#include "urma_0842_urma_set_jfs_opt_failed_exec_ops_set_jfs_opt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0842UrmaSetJfsOptFailedExecOpsSetJfsOpt> g_urma("urma_0842");

bool Urma0842UrmaSetJfsOptFailedExecOpsSetJfsOpt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec ops->set_jfs_opt."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0842UrmaSetJfsOptFailedExecOpsSetJfsOpt::GetName() const
{
    return "urma_set_jfs_opt Failed to exec ops->set_jfs_opt.";
}

std::string Urma0842UrmaSetJfsOptFailedExecOpsSetJfsOpt::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `status != URMA_SUCCESS`；该路径返回 status";
}

RootCause Urma0842UrmaSetJfsOptFailedExecOpsSetJfsOpt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0842UrmaSetJfsOptFailedExecOpsSetJfsOpt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0842UrmaSetJfsOptFailedExecOpsSetJfsOpt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec ops->set_jfs_opt.";
}

std::string Urma0842UrmaSetJfsOptFailedExecOpsSetJfsOpt::GetId() const
{
    return "urma_0842";
}
} // namespace diag
