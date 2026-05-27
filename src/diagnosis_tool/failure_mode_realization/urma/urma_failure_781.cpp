#include "urma_failure_781.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure781> g_urma("urma_781");

bool UrmaFailure781::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_order_type' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure781::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供create_jfs操作实现无效导致创建JFS失败";
}

std::string UrmaFailure781::GetRootCauseDesc() const
{
    return "函数用于创建JFS，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、provider未提供create_"
           "jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure781::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure781::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure781::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_order_type，Invalid parameter.";
}

std::string UrmaFailure781::GetId() const
{
    return "urma_781";
}

} // namespace diag
