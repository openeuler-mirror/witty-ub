#include "urma_failure_212.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure212> g_urma("urma_212");

bool UrmaFailure212::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jetty_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, index' | grep -F 'jetty in the array is NULL.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure212::GetName() const
{
    return "Jetty对象无效导致删除Jetty失败";
}

std::string UrmaFailure212::GetRootCauseDesc() const
{
    return "函数用于删除Jetty，调用方传入的Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure212::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure212::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure212::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jetty_batch，Invalid parameter, index，jetty in the array is NULL.";
}

std::string UrmaFailure212::GetId() const
{
    return "urma_212";
}

} // namespace diag
