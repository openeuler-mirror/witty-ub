#include "urma_failure_131.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure131> g_urma("urma_131");

bool UrmaFailure131::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure131::GetName() const
{
    return "URMA context、Jetty对象无效导致删除Jetty失败";
}

std::string UrmaFailure131::GetRootCauseDesc() const
{
    return "函数用于删除Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure131::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure131::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure131::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_delete_jetty，Invalid parameter";
}

std::string UrmaFailure131::GetId() const
{
    return "urma_131";
}

} // namespace diag
