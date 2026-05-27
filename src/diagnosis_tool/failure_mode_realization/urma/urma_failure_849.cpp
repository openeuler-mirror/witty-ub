#include "urma_failure_849.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure849> g_urma("urma_849");

bool UrmaFailure849::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_user_ctl' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to excecute user_ctl, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure849::GetName() const
{
    return "执行context过程中依赖步骤失败";
}

std::string UrmaFailure849::GetRootCauseDesc() const
{
    return "函数用于执行context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA"
           "操作失败。";
}

RootCause UrmaFailure849::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure849::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure849::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_user_ctl，Failed to excecute user_ctl, ret:";
}

std::string UrmaFailure849::GetId() const
{
    return "urma_849";
}

} // namespace diag
