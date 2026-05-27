#include "urma_failure_305.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure305> g_urma("urma_305");

bool UrmaFailure305::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_tpn' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure305::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表、Jetty对象无效导致获取TPN失败";
}

std::string UrmaFailure305::GetRootCauseDesc() const
{
    return "函数用于获取TPN，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure305::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure305::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure305::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_tpn，Invalid parameter.。";
}

std::string UrmaFailure305::GetId() const
{
    return "urma_305";
}

} // namespace diag
