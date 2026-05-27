#include "urma_failure_564.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure564> g_urma("urma_564");

bool UrmaFailure564::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'schedule_recv' "
                                                         "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'No active port'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure564::GetName() const
{
    return "激活端口过程中依赖步骤失败";
}

std::string UrmaFailure564::GetRootCauseDesc() const
{
    return "函数用于激活端口，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure564::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure564::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure564::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：schedule_recv，No active port";
}

std::string UrmaFailure564::GetId() const
{
    return "urma_564";
}

} // namespace diag
