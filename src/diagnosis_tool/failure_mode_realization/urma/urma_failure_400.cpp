#include "urma_failure_400.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure400> g_urma("urma_400");

bool UrmaFailure400::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure400::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_jfr操作实现无效导致分配JFR失败";
}

std::string UrmaFailure400::GetRootCauseDesc() const
{
    return "函数用于分配JFR，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_"
           "jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure400::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure400::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure400::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_alloc_jfr，Invalid parameter.";
}

std::string UrmaFailure400::GetId() const
{
    return "urma_400";
}

} // namespace diag
