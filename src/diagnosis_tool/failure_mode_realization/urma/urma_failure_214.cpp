#include "urma_failure_214.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure214> g_urma("urma_214");

bool UrmaFailure214::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jetty_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure214::GetName() const
{
    return "URMA context、设备对象、sysfs设备信息、provider操作表、Jetty对象无效导致删除Jetty失败";
}

std::string UrmaFailure214::GetRootCauseDesc() const
{
    return "函数用于删除Jetty，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure214::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure214::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure214::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jetty_batch，Invalid parameter, index:";
}

std::string UrmaFailure214::GetId() const
{
    return "urma_214";
}

} // namespace diag
