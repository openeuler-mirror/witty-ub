#include "urma_failure_414.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure414> g_urma("urma_414");

bool UrmaFailure414::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_get_async_event' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure414::GetName() const
{
    return "URMA context无效导致获取EID失败";
}

std::string UrmaFailure414::GetRootCauseDesc() const
{
    return "函数用于获取EID，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure414::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure414::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure414::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_get_async_event，Invalid parameter";
}

std::string UrmaFailure414::GetId() const
{
    return "urma_414";
}

} // namespace diag
