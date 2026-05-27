#include "urma_failure_681.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure681> g_urma("urma_681");

bool UrmaFailure681::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfr_batch' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure681::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表、JFR对象无效导致删除JFR失败";
}

std::string UrmaFailure681::GetRootCauseDesc() const
{
    return "函数用于删除JFR，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure681::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure681::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure681::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfr_batch，Invalid parameter, index:。";
}

std::string UrmaFailure681::GetId() const
{
    return "urma_681";
}

} // namespace diag
