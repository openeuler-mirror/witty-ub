#include "urma_failure_235.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure235> g_urma("urma_235");

bool UrmaFailure235::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_bind_jetty_ex' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure235::GetName() const
{
    return "URMA "
           "context、provider操作表、Jetty对象、目标Jetty对象、provider未提供bind_jetty_"
           "ex操作实现无效导致绑定Jetty失败";
}

std::string UrmaFailure235::GetRootCauseDesc() const
{
    return "函数用于绑定Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象、目标Jetty对象、provider未提供bind_jetty_"
           "ex操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure235::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure235::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure235::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_bind_jetty_ex，Invalid parameter.。";
}

std::string UrmaFailure235::GetId() const
{
    return "urma_235";
}

} // namespace diag
