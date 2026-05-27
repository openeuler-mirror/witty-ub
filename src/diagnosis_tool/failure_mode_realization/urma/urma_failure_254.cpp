#include "urma_failure_254.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure254> g_urma("urma_254");

bool UrmaFailure254::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_bind_jetty_async' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure254::GetName() const
{
    return "URMA "
           "context、provider操作表、Jetty对象、目标Jetty对象、provider未提供bind_jetty_"
           "async操作实现无效导致绑定Jetty失败";
}

std::string UrmaFailure254::GetRootCauseDesc() const
{
    return "函数用于绑定Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象、目标Jetty对象、provider未提供bind_jetty_"
           "async操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure254::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure254::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure254::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_bind_jetty_async，Invalid parameter.。";
}

std::string UrmaFailure254::GetId() const
{
    return "urma_254";
}

} // namespace diag
