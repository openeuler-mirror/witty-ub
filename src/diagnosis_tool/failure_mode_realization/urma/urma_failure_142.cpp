#include "urma_failure_142.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure142> g_urma("urma_142");

bool UrmaFailure142::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_unimport_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure142::GetName() const
{
    return "URMA context、目标Jetty对象无效导致解除导入Jetty失败";
}

std::string UrmaFailure142::GetRootCauseDesc() const
{
    return "函数用于解除导入Jetty，调用方传入的URMA "
           "context、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure142::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure142::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure142::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_unimport_jetty，Invalid parameter";
}

std::string UrmaFailure142::GetId() const
{
    return "urma_142";
}

} // namespace diag
