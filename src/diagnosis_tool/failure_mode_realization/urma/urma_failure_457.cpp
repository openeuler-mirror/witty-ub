#include "urma_failure_457.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure457> g_urma("urma_457");

bool UrmaFailure457::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_jfs_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to exec ops->get_jfs_opt.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure457::GetName() const
{
    return "获取JFS过程中依赖步骤失败";
}

std::string UrmaFailure457::GetRootCauseDesc() const
{
    return "函数用于获取JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure457::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure457::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure457::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jfs_opt，Failed to exec ops->get_jfs_opt.。";
}

std::string UrmaFailure457::GetId() const
{
    return "urma_457";
}

} // namespace diag
