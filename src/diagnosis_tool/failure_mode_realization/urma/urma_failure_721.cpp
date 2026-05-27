#include "urma_failure_721.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure721> g_urma("urma_721");

bool UrmaFailure721::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_ack_async_event' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure721::GetName() const
{
    return "确认URMA资源所需输入对象无效导致确认URMA资源失败";
}

std::string UrmaFailure721::GetRootCauseDesc() const
{
    return "函数用于确认URMA资源，调用方传入的确认URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure721::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure721::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure721::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_ack_async_event，Invalid parameter";
}

std::string UrmaFailure721::GetId() const
{
    return "urma_721";
}

} // namespace diag
