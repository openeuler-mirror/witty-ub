#include "urma_failure_282.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure282> g_urma("urma_282");

bool UrmaFailure282::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure282::GetName() const
{
    return "provider操作表、Jetty对象无效导致去激活Jetty失败";
}

std::string UrmaFailure282::GetRootCauseDesc() const
{
    return "函数用于去激活Jetty，调用方传入的provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure282::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure282::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure282::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_deactive_jetty，Invalid parameter.";
}

std::string UrmaFailure282::GetId() const
{
    return "urma_282";
}

} // namespace diag
