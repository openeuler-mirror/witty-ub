#include "urma_failure_227.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure227> g_urma("urma_227");

bool UrmaFailure227::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_bind_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure227::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表、Jetty对象、目标Jetty对象无效导致绑定Jetty失败";
}

std::string UrmaFailure227::GetRootCauseDesc() const
{
    return "函数用于绑定Jetty，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成"
           "本次URMA操作。";
}

RootCause UrmaFailure227::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure227::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure227::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_bind_jetty，Invalid parameter.";
}

std::string UrmaFailure227::GetId() const
{
    return "urma_227";
}

} // namespace diag
