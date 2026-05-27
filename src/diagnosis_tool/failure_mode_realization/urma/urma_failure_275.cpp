#include "urma_failure_275.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure275> g_urma("urma_275");

bool UrmaFailure275::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure275::GetName() const
{
    return "URMA context、provider操作表、Jetty对象无效导致激活Jetty失败";
}

std::string UrmaFailure275::GetRootCauseDesc() const
{
    return "函数用于激活Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure275::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure275::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure275::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_active_jetty，Invalid parameter.";
}

std::string UrmaFailure275::GetId() const
{
    return "urma_275";
}

} // namespace diag
