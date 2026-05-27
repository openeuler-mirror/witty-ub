#include "urma_failure_217.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure217> g_urma("urma_217");

bool UrmaFailure217::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_flush_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure217::GetName() const
{
    return "URMA context、provider操作表、Jetty对象、provider未提供flush_jetty操作实现无效导致刷出Jetty失败";
}

std::string UrmaFailure217::GetRootCauseDesc() const
{
    return "函数用于刷出Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象、provider未提供flush_"
           "jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure217::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure217::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure217::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_flush_jetty，Invalid parameter.";
}

std::string UrmaFailure217::GetId() const
{
    return "urma_217";
}

} // namespace diag
