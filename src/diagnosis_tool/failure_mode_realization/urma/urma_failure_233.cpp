#include "urma_failure_233.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure233> g_urma("urma_233");

bool UrmaFailure233::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_bind_jetty_ex' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure233::GetName() const
{
    return "URMA "
           "context、provider操作表、Jetty对象、目标Jetty对象、provider未提供bind_jetty_"
           "ex操作实现无效导致绑定Jetty失败";
}

std::string UrmaFailure233::GetRootCauseDesc() const
{
    return "函数用于绑定Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象、目标Jetty对象、provider未提供bind_jetty_"
           "ex操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure233::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure233::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure233::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_bind_jetty_ex，Invalid parameter.";
}

std::string UrmaFailure233::GetId() const
{
    return "urma_233";
}

} // namespace diag
