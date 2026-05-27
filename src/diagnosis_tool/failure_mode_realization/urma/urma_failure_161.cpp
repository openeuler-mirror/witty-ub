#include "urma_failure_161.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure161> g_urma("urma_161");

bool UrmaFailure161::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_active_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid flag.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure161::GetName() const
{
    return "JFR对象、Jetty对象无效导致激活Jetty失败";
}

std::string UrmaFailure161::GetRootCauseDesc() const
{
    return "函数用于激活Jetty，调用方传入的JFR对象、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure161::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure161::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure161::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_active_jetty，Invalid flag.";
}

std::string UrmaFailure161::GetId() const
{
    return "urma_161";
}

} // namespace diag
