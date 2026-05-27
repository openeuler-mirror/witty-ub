#include "urma_failure_237.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure237> g_urma("urma_237");

bool UrmaFailure237::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_advise_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure237::GetName() const
{
    return "URMA context、provider操作表、Jetty对象、目标Jetty对象无效导致解绑Jetty失败";
}

std::string UrmaFailure237::GetRootCauseDesc() const
{
    return "函数用于解绑Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure237::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure237::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure237::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_advise_jetty，Invalid parameter.";
}

std::string UrmaFailure237::GetId() const
{
    return "urma_237";
}

} // namespace diag
