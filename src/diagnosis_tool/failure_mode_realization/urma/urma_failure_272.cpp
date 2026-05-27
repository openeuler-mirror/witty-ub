#include "urma_failure_272.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure272> g_urma("urma_272");

bool UrmaFailure272::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_jetty_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure272::GetName() const
{
    return "URMA context、provider操作表、Jetty对象、provider未提供get_jetty_opt操作实现无效导致获取Jetty失败";
}

std::string UrmaFailure272::GetRootCauseDesc() const
{
    return "函数用于获取Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象、provider未提供get_jetty_"
           "opt操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure272::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure272::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure272::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_get_jetty_opt，Invalid parameter.";
}

std::string UrmaFailure272::GetId() const
{
    return "urma_272";
}

} // namespace diag
