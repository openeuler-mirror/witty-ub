#include "urma_failure_498.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure498> g_urma("urma_498");

bool UrmaFailure498::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_uasid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure498::GetName() const
{
    return "URMA context无效导致获取context失败";
}

std::string UrmaFailure498::GetRootCauseDesc() const
{
    return "函数用于获取context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure498::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure498::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure498::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_get_uasid，Invalid parameter.";
}

std::string UrmaFailure498::GetId() const
{
    return "urma_498";
}

} // namespace diag
