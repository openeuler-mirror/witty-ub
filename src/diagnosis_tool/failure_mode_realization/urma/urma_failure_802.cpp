#include "urma_failure_802.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure802> g_urma("urma_802");

bool UrmaFailure802::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure802::GetName() const
{
    return "URMA "
           "context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jfr操作实现无效导致去激活JFS失败";
}

std::string UrmaFailure802::GetRootCauseDesc() const
{
    return "函数用于去激活JFS，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、provider未提供create_"
           "jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure802::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure802::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure802::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_deactive_jfs，Invalid parameter.";
}

std::string UrmaFailure802::GetId() const
{
    return "urma_802";
}

} // namespace diag
