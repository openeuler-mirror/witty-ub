#include "urma_failure_302.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure302> g_urma("urma_302");

bool UrmaFailure302::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_tpn' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure302::GetName() const
{
    return "URMA context、provider操作表、Jetty对象、provider未提供get_tpn操作实现无效导致获取TPN失败";
}

std::string UrmaFailure302::GetRootCauseDesc() const
{
    return "函数用于获取TPN，调用方传入的URMA "
           "context、provider操作表、Jetty对象、provider未提供get_"
           "tpn操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure302::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure302::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure302::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_get_tpn，Invalid parameter.";
}

std::string UrmaFailure302::GetId() const
{
    return "urma_302";
}

} // namespace diag
