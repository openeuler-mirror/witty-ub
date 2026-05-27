#include "urma_failure_165.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure165> g_urma("urma_165");

bool UrmaFailure165::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_deactive_jetty' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure165::GetName() const
{
    return "URMA context、Jetty对象无效导致去激活Jetty失败";
}

std::string UrmaFailure165::GetRootCauseDesc() const
{
    return "函数用于去激活Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure165::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure165::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure165::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_deactive_jetty，Invalid parameter。";
}

std::string UrmaFailure165::GetId() const
{
    return "urma_165";
}

} // namespace diag
