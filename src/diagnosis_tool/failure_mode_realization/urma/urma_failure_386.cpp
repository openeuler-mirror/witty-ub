#include "urma_failure_386.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure386> g_urma("urma_386");

bool UrmaFailure386::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure386::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_jfc操作实现无效导致分配JFC失败";
}

std::string UrmaFailure386::GetRootCauseDesc() const
{
    return "函数用于分配JFC，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_"
           "jfc操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure386::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure386::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure386::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_alloc_jfc，Invalid parameter.";
}

std::string UrmaFailure386::GetId() const
{
    return "urma_386";
}

} // namespace diag
