#include "urma_failure_493.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure493> g_urma("urma_493");

bool UrmaFailure493::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_device' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure493::GetName() const
{
    return "设备对象、sysfs设备信息无效导致查询设备失败";
}

std::string UrmaFailure493::GetRootCauseDesc() const
{
    return "函数用于查询设备，调用方传入的设备对象、sysfs设备信息不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure493::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure493::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure493::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_device，Invalid parameter.。";
}

std::string UrmaFailure493::GetId() const
{
    return "urma_493";
}

} // namespace diag
