#include "urma_failure_289.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure289> g_urma("urma_289");

bool UrmaFailure289::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_ack_notify' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'max_jetty_in_jetty_grp' | grep -F 'is err.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure289::GetName() const
{
    return "确认Jetty过程中依赖步骤失败";
}

std::string UrmaFailure289::GetRootCauseDesc() const
{
    return "函数用于确认Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure289::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure289::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure289::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_ack_notify，max_jetty_in_jetty_grp，is err.";
}

std::string UrmaFailure289::GetId() const
{
    return "urma_289";
}

} // namespace diag
