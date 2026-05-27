#include "urma_failure_208.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure208> g_urma("urma_208");

bool UrmaFailure208::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure208::GetName() const
{
    return "URMA context、provider操作表、Jetty对象、provider未提供delete_jetty操作实现无效导致删除Jetty失败";
}

std::string UrmaFailure208::GetRootCauseDesc() const
{
    return "函数用于删除Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象、provider未提供delete_"
           "jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure208::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure208::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure208::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jetty，Invalid parameter.";
}

std::string UrmaFailure208::GetId() const
{
    return "urma_208";
}

} // namespace diag
