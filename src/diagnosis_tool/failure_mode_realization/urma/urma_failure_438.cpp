#include "urma_failure_438.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure438> g_urma("urma_438");

bool UrmaFailure438::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_async_event' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure438::GetName() const
{
    return "URMA context无效导致获取JFC失败";
}

std::string UrmaFailure438::GetRootCauseDesc() const
{
    return "函数用于获取JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure438::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure438::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure438::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_get_async_event，Invalid parameter";
}

std::string UrmaFailure438::GetId() const
{
    return "urma_438";
}

} // namespace diag
