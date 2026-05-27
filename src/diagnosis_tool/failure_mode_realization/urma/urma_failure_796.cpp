#include "urma_failure_796.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure796> g_urma("urma_796");

bool UrmaFailure796::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to exec ops->active_jfs.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure796::GetName() const
{
    return "激活JFS过程中依赖步骤失败";
}

std::string UrmaFailure796::GetRootCauseDesc() const
{
    return "函数用于激活JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure796::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure796::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure796::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_active_jfs，Failed to exec ops->active_jfs.";
}

std::string UrmaFailure796::GetId() const
{
    return "urma_796";
}

} // namespace diag
