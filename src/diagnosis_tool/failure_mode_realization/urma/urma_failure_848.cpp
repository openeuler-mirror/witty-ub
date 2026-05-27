#include "urma_failure_848.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure848> g_urma("urma_848");

bool UrmaFailure848::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_user_ctl' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure848::GetName() const
{
    return "URMA context、provider操作表、provider未提供user_ctl操作实现无效导致执行context失败";
}

std::string UrmaFailure848::GetRootCauseDesc() const
{
    return "函数用于执行context，调用方传入的URMA "
           "context、provider操作表、provider未提供user_ctl操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure848::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure848::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure848::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_user_ctl，Invalid parameter.";
}

std::string UrmaFailure848::GetId() const
{
    return "urma_848";
}

} // namespace diag
