#include "urma_failure_264.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure264> g_urma("urma_264");

bool UrmaFailure264::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jetty_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'invalid opt id or opt len'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure264::GetName() const
{
    return "provider操作表、Jetty对象无效导致设置Jetty失败";
}

std::string UrmaFailure264::GetRootCauseDesc() const
{
    return "函数用于设置Jetty，调用方传入的provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure264::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure264::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure264::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_jetty_opt，invalid opt id or opt len";
}

std::string UrmaFailure264::GetId() const
{
    return "urma_264";
}

} // namespace diag
