#include "urma_failure_051.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure051> g_urma("urma_051");

bool UrmaFailure051::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_stop_perf' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Urma perf "
        "failed to uninitialize performance record context'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure051::GetName() const
{
    return "执行context过程中依赖步骤失败";
}

std::string UrmaFailure051::GetRootCauseDesc() const
{
    return "函数用于执行context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA"
           "操作失败。";
}

RootCause UrmaFailure051::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure051::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure051::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_stop_perf，Urma perf failed to uninitialize performance record "
           "context。";
}

std::string UrmaFailure051::GetId() const
{
    return "urma_051";
}

} // namespace diag
