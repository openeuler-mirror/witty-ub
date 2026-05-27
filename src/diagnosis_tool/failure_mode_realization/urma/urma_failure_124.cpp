#include "urma_failure_124.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure124> g_urma("urma_124");

bool UrmaFailure124::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_unadvise_jetty' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure124::GetName() const
{
    return "URMA context、JFR对象、Jetty对象、目标Jetty对象无效导致去激活Jetty失败";
}

std::string UrmaFailure124::GetRootCauseDesc() const
{
    return "函数用于去激活Jetty，调用方传入的URMA "
           "context、JFR对象、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure124::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure124::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure124::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unadvise_jetty，Invalid parameter。";
}

std::string UrmaFailure124::GetId() const
{
    return "urma_124";
}

} // namespace diag
