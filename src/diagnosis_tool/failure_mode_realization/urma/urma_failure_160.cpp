#include "urma_failure_160.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure160> g_urma("urma_160");

bool UrmaFailure160::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_active_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure160::GetName() const
{
    return "URMA context、Jetty对象无效导致激活Jetty失败";
}

std::string UrmaFailure160::GetRootCauseDesc() const
{
    return "函数用于激活Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure160::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure160::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure160::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_active_jetty，Invalid parameter";
}

std::string UrmaFailure160::GetId() const
{
    return "urma_160";
}

} // namespace diag
