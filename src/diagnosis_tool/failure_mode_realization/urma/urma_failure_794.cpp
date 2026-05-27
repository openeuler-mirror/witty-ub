#include "urma_failure_794.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure794> g_urma("urma_794");

bool UrmaFailure794::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure794::GetName() const
{
    return "URMA "
           "context、设备对象、sysfs设备信息、provider操作表、JFS对象、provider未提供active_"
           "jfs操作实现无效导致激活JFS失败";
}

std::string UrmaFailure794::GetRootCauseDesc() const
{
    return "函数用于激活JFS，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、JFS对象、provider未提供active_"
           "jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure794::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure794::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure794::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_active_jfs，Invalid parameter.";
}

std::string UrmaFailure794::GetId() const
{
    return "urma_794";
}

} // namespace diag
