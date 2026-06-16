#include "urma_failure_216.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure216> g_urma("urma_216");

bool UrmaFailure216::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jetty_batch' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure216::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表、Jetty对象无效导致删除Jetty失败";
}

std::string UrmaFailure216::GetRootCauseDesc() const
{
    return "函数用于删除Jetty，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure216::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure216::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure216::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty_batch，Invalid parameter, index:。";
}

std::string UrmaFailure216::GetId() const
{
    return "urma_216";
}

} // namespace diag
