#include "urma_failure_236.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure236> g_urma("urma_236");

bool UrmaFailure236::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unbind_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure236::GetName() const
{
    return "URMA context、provider操作表、Jetty对象、provider未提供unbind_jetty操作实现无效导致解绑Jetty失败";
}

std::string UrmaFailure236::GetRootCauseDesc() const
{
    return "函数用于解绑Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象、provider未提供unbind_"
           "jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure236::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure236::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure236::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_unbind_jetty，Invalid parameter.";
}

std::string UrmaFailure236::GetId() const
{
    return "urma_236";
}

} // namespace diag
