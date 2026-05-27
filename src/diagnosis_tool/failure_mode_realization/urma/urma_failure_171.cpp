#include "urma_failure_171.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure171> g_urma("urma_171");

bool UrmaFailure171::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_unbind_jetty_async' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure171::GetName() const
{
    return "URMA context、Jetty对象、目标Jetty对象无效导致解绑Jetty失败";
}

std::string UrmaFailure171::GetRootCauseDesc() const
{
    return "函数用于解绑Jetty，调用方传入的URMA "
           "context、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure171::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure171::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure171::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unbind_jetty_async，Invalid parameter。";
}

std::string UrmaFailure171::GetId() const
{
    return "urma_171";
}

} // namespace diag
