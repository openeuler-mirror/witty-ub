#include "urma_failure_832.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure832> g_urma("urma_832");

bool UrmaFailure832::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_ack_notify' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure832::GetName() const
{
    return "URMA "
           "context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jetty_"
           "grp操作实现无效导致确认Jetty失败";
}

std::string UrmaFailure832::GetRootCauseDesc() const
{
    return "函数用于确认Jetty，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jetty_"
           "grp操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure832::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure832::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure832::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_ack_notify，Invalid parameter.";
}

std::string UrmaFailure832::GetId() const
{
    return "urma_832";
}

} // namespace diag
