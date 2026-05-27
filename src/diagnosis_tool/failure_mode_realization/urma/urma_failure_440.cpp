#include "urma_failure_440.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure440> g_urma("urma_440");

bool UrmaFailure440::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_query_device_attr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure440::GetName() const
{
    return "URMA context、sysfs设备信息无效导致查询设备失败";
}

std::string UrmaFailure440::GetRootCauseDesc() const
{
    return "函数用于查询设备，调用方传入的URMA context、sysfs设备信息不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure440::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure440::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure440::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_query_device_attr，Invalid parameter.";
}

std::string UrmaFailure440::GetId() const
{
    return "urma_440";
}

} // namespace diag
