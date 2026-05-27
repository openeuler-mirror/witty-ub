#include "urma_failure_280.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure280> g_urma("urma_280");

bool UrmaFailure280::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure280::GetName() const
{
    return "URMA context、provider操作表、JFR对象、Jetty对象、provider未提供active_jetty操作实现无效导致激活Jetty失败";
}

std::string UrmaFailure280::GetRootCauseDesc() const
{
    return "函数用于激活Jetty，调用方传入的URMA "
           "context、provider操作表、JFR对象、Jetty对象、provider未提供active_"
           "jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure280::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure280::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure280::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_active_jetty，Invalid parameter.";
}

std::string UrmaFailure280::GetId() const
{
    return "urma_280";
}

} // namespace diag
