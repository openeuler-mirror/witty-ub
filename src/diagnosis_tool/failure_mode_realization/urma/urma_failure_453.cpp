#include "urma_failure_453.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure453> g_urma("urma_453");

bool UrmaFailure453::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_jfs_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to exec ops->get_jfs_opt.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure453::GetName() const
{
    return "获取JFS过程中依赖步骤失败";
}

std::string UrmaFailure453::GetRootCauseDesc() const
{
    return "函数用于获取JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure453::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure453::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure453::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_get_jfs_opt，Failed to exec ops->get_jfs_opt.";
}

std::string UrmaFailure453::GetId() const
{
    return "urma_453";
}

} // namespace diag
