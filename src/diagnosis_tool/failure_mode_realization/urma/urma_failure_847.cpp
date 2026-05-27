#include "urma_failure_847.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure847> g_urma("urma_847");

bool UrmaFailure847::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_user_ctl' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure847::GetName() const
{
    return "URMA context、provider操作表无效导致确认context失败";
}

std::string UrmaFailure847::GetRootCauseDesc() const
{
    return "函数用于确认context，调用方传入的URMA "
           "context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure847::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure847::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure847::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_user_ctl，Invalid parameter.";
}

std::string UrmaFailure847::GetId() const
{
    return "urma_847";
}

} // namespace diag
