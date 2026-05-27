#include "urma_failure_756.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure756> g_urma("urma_756");

bool UrmaFailure756::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_ack_async_event' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure756::GetName() const
{
    return "JFS对象、JFR对象、Jetty对象无效导致确认JFC失败";
}

std::string UrmaFailure756::GetRootCauseDesc() const
{
    return "函数用于确认JFC，调用方传入的JFS对象、JFR对象、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure756::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure756::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure756::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_ack_async_event，Invalid parameter";
}

std::string UrmaFailure756::GetId() const
{
    return "urma_756";
}

} // namespace diag
