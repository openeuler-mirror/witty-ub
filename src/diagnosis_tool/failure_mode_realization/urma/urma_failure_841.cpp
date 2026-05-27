#include "urma_failure_841.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure841> g_urma("urma_841");

bool UrmaFailure841::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_ack_notify' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure841::GetName() const
{
    return "URMA "
           "context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jetty_"
           "grp操作实现无效导致确认Jetty失败";
}

std::string UrmaFailure841::GetRootCauseDesc() const
{
    return "函数用于确认Jetty，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jetty_"
           "grp操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure841::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure841::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure841::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ack_notify，Invalid parameter.。";
}

std::string UrmaFailure841::GetId() const
{
    return "urma_841";
}

} // namespace diag
