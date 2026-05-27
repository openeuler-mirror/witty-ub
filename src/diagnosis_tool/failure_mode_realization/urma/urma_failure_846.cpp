#include "urma_failure_846.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure846> g_urma("urma_846");

bool UrmaFailure846::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_ack_async_event' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter with ops nullptr.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure846::GetName() const
{
    return "URMA context、provider操作表无效导致确认context失败";
}

std::string UrmaFailure846::GetRootCauseDesc() const
{
    return "函数用于确认context，调用方传入的URMA "
           "context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure846::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure846::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure846::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_ack_async_event，Invalid parameter with ops nullptr.";
}

std::string UrmaFailure846::GetId() const
{
    return "urma_846";
}

} // namespace diag
