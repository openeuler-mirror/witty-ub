#include "urma_failure_229.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure229> g_urma("urma_229");

bool UrmaFailure229::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_bind_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure229::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表、Jetty对象、目标Jetty对象无效导致绑定Jetty失败";
}

std::string UrmaFailure229::GetRootCauseDesc() const
{
    return "函数用于绑定Jetty，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成"
           "本次URMA操作。";
}

RootCause UrmaFailure229::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure229::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure229::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_bind_jetty，Invalid parameter.。";
}

std::string UrmaFailure229::GetId() const
{
    return "urma_229";
}

} // namespace diag
