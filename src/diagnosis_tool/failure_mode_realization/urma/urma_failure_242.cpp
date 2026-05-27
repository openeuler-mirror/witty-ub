#include "urma_failure_242.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure242> g_urma("urma_242");

bool UrmaFailure242::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unadvise_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure242::GetName() const
{
    return "URMA context、设备对象、provider操作表、Jetty对象、目标Jetty对象无效导致执行Jetty失败";
}

std::string UrmaFailure242::GetRootCauseDesc() const
{
    return "函数用于执行Jetty，调用方传入的URMA "
           "context、设备对象、provider操作表、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure242::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure242::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure242::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_unadvise_jetty，Invalid parameter.";
}

std::string UrmaFailure242::GetId() const
{
    return "urma_242";
}

} // namespace diag
