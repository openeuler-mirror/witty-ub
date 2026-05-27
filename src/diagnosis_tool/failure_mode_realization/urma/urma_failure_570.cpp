#include "urma_failure_570.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure570> g_urma("urma_570");

bool UrmaFailure570::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'schedule_recv' "
                                                         "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'No active port'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure570::GetName() const
{
    return "激活端口过程中依赖步骤失败";
}

std::string UrmaFailure570::GetRootCauseDesc() const
{
    return "函数用于激活端口，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure570::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure570::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure570::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：schedule_recv，No active port。";
}

std::string UrmaFailure570::GetId() const
{
    return "urma_570";
}

} // namespace diag
