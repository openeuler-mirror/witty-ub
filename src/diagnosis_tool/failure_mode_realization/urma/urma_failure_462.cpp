#include "urma_failure_462.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure462> g_urma("urma_462");

bool UrmaFailure462::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_async_event' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure462::GetName() const
{
    return "URMA context、provider操作表、provider未提供get_async_event操作实现无效导致获取context失败";
}

std::string UrmaFailure462::GetRootCauseDesc() const
{
    return "函数用于获取context，调用方传入的URMA "
           "context、provider操作表、provider未提供get_async_"
           "event操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure462::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure462::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure462::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_get_async_event，Invalid parameter.";
}

std::string UrmaFailure462::GetId() const
{
    return "urma_462";
}

} // namespace diag
