#include "urma_failure_092.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure092> g_urma("urma_092");

bool UrmaFailure092::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_get_async_event' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'failed to get invalid jetty.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure092::GetName() const
{
    return "URMA context、Jetty对象无效导致获取Jetty失败";
}

std::string UrmaFailure092::GetRootCauseDesc() const
{
    return "函数用于获取Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure092::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure092::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure092::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_get_async_event，failed to get invalid jetty.";
}

std::string UrmaFailure092::GetId() const
{
    return "urma_092";
}

} // namespace diag
