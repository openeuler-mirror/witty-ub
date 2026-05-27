#include "urma_failure_771.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure771> g_urma("urma_771");

bool UrmaFailure771::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure771::GetName() const
{
    return "provider操作表无效导致激活JFC失败";
}

std::string UrmaFailure771::GetRootCauseDesc() const
{
    return "函数用于激活JFC，调用方传入的provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure771::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure771::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure771::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_active_jfc，Invalid parameter.";
}

std::string UrmaFailure771::GetId() const
{
    return "urma_771";
}

} // namespace diag
