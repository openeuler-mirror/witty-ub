#include "urma_failure_271.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure271> g_urma("urma_271");

bool UrmaFailure271::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_jetty_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure271::GetName() const
{
    return "Jetty对象无效导致获取Jetty失败";
}

std::string UrmaFailure271::GetRootCauseDesc() const
{
    return "函数用于获取Jetty，调用方传入的Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure271::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure271::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure271::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_get_jetty_opt，Invalid parameter.";
}

std::string UrmaFailure271::GetId() const
{
    return "urma_271";
}

} // namespace diag
