#include "urma_failure_489.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure489> g_urma("urma_489");

bool UrmaFailure489::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_device' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure489::GetName() const
{
    return "设备对象、sysfs设备信息无效导致查询设备失败";
}

std::string UrmaFailure489::GetRootCauseDesc() const
{
    return "函数用于查询设备，调用方传入的设备对象、sysfs设备信息不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure489::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure489::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure489::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_query_device，Invalid parameter.";
}

std::string UrmaFailure489::GetId() const
{
    return "urma_489";
}

} // namespace diag
