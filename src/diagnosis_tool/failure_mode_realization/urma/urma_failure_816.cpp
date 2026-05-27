#include "urma_failure_816.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure816> g_urma("urma_816");

bool UrmaFailure816::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_ctrlplane_compat' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure816::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表、目标Jetty对象无效导致导入context失败";
}

std::string UrmaFailure816::GetRootCauseDesc() const
{
    return "函数用于导入context，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作"
           "。";
}

RootCause UrmaFailure816::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure816::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure816::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_ctrlplane_compat，Invalid parameter.。";
}

std::string UrmaFailure816::GetId() const
{
    return "urma_816";
}

} // namespace diag
