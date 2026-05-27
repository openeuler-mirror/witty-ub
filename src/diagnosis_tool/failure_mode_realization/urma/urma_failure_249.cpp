#include "urma_failure_249.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure249> g_urma("urma_249");

bool UrmaFailure249::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_bind_jetty_async' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure249::GetName() const
{
    return "URMA context、Jetty对象、目标Jetty对象无效导致绑定Jetty失败";
}

std::string UrmaFailure249::GetRootCauseDesc() const
{
    return "函数用于绑定Jetty，调用方传入的URMA "
           "context、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure249::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure249::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure249::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_bind_jetty_async，Invalid parameter.";
}

std::string UrmaFailure249::GetId() const
{
    return "urma_249";
}

} // namespace diag
