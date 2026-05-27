#include "urma_failure_262.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure262> g_urma("urma_262");

bool UrmaFailure262::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jetty_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure262::GetName() const
{
    return "URMA context、Jetty对象无效导致设置Jetty失败";
}

std::string UrmaFailure262::GetRootCauseDesc() const
{
    return "函数用于设置Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure262::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure262::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure262::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_jetty_opt，Invalid parameter.";
}

std::string UrmaFailure262::GetId() const
{
    return "urma_262";
}

} // namespace diag
