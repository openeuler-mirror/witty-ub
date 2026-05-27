#include "urma_failure_378.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure378> g_urma("urma_378");

bool UrmaFailure378::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_alloc_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure378::GetName() const
{
    return "URMA context、JFR对象、Jetty对象、目标Jetty对象无效导致分配JFR失败";
}

std::string UrmaFailure378::GetRootCauseDesc() const
{
    return "函数用于分配JFR，调用方传入的URMA "
           "context、JFR对象、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure378::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure378::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure378::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_alloc_jfr，Invalid parameter";
}

std::string UrmaFailure378::GetId() const
{
    return "urma_378";
}

} // namespace diag
