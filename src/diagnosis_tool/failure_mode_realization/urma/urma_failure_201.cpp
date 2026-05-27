#include "urma_failure_201.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure201> g_urma("urma_201");

bool UrmaFailure201::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure201::GetName() const
{
    return "URMA context、provider操作表、Jetty对象无效导致释放Jetty失败";
}

std::string UrmaFailure201::GetRootCauseDesc() const
{
    return "函数用于释放Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure201::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure201::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure201::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_free_jetty，Invalid parameter.";
}

std::string UrmaFailure201::GetId() const
{
    return "urma_201";
}

} // namespace diag
