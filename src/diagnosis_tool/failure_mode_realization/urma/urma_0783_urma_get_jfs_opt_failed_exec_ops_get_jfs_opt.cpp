#include "urma_0783_urma_get_jfs_opt_failed_exec_ops_get_jfs_opt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0783UrmaGetJfsOptFailedExecOpsGetJfsOpt> g_urma("urma_0783");

bool Urma0783UrmaGetJfsOptFailedExecOpsGetJfsOpt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec ops->get_jfs_opt."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0783UrmaGetJfsOptFailedExecOpsGetJfsOpt::GetName() const
{
    return "urma_get_jfs_opt Failed to exec ops->get_jfs_opt.";
}

std::string Urma0783UrmaGetJfsOptFailedExecOpsGetJfsOpt::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `status != URMA_SUCCESS`；该路径返回 status";
}

RootCause Urma0783UrmaGetJfsOptFailedExecOpsGetJfsOpt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0783UrmaGetJfsOptFailedExecOpsGetJfsOpt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0783UrmaGetJfsOptFailedExecOpsGetJfsOpt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec ops->get_jfs_opt.";
}

std::string Urma0783UrmaGetJfsOptFailedExecOpsGetJfsOpt::GetId() const
{
    return "urma_0783";
}
} // namespace diag
