#include "urma_failure_765.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure765> g_urma("urma_765");

bool UrmaFailure765::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_ack_async_event' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure765::GetName() const
{
    return "JFS对象、JFR对象、Jetty对象无效导致确认JFC失败";
}

std::string UrmaFailure765::GetRootCauseDesc() const
{
    return "函数用于确认JFC，调用方传入的JFS对象、JFR对象、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure765::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure765::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure765::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_ack_async_event，Invalid parameter。";
}

std::string UrmaFailure765::GetId() const
{
    return "urma_765";
}

} // namespace diag
