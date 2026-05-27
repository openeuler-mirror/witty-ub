#include "urma_failure_317.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure317> g_urma("urma_317");

bool UrmaFailure317::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_post_jetty_send_wr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure317::GetName() const
{
    return "Jetty对象、WR对象无效导致投递Jetty失败";
}

std::string UrmaFailure317::GetRootCauseDesc() const
{
    return "函数用于投递Jetty，调用方传入的Jetty对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure317::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure317::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure317::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_post_jetty_send_wr，Invalid parameter.";
}

std::string UrmaFailure317::GetId() const
{
    return "urma_317";
}

} // namespace diag
