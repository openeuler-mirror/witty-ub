#include "urma_failure_221.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure221> g_urma("urma_221");

bool UrmaFailure221::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_flush_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure221::GetName() const
{
    return "URMA context、provider操作表无效导致刷出Jetty失败";
}

std::string UrmaFailure221::GetRootCauseDesc() const
{
    return "函数用于刷出Jetty，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure221::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure221::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure221::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_flush_jetty，Invalid parameter.";
}

std::string UrmaFailure221::GetId() const
{
    return "urma_221";
}

} // namespace diag
