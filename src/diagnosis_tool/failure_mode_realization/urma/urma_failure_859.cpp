#include "urma_failure_859.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure859> g_urma("urma_859");

bool UrmaFailure859::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_validate_driver' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid driver name length.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure859::GetName() const
{
    return "provider操作表无效导致注销URMA资源失败";
}

std::string UrmaFailure859::GetRootCauseDesc() const
{
    return "函数用于注销URMA资源，调用方传入的provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure859::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure859::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure859::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_validate_driver，Invalid driver name length.";
}

std::string UrmaFailure859::GetId() const
{
    return "urma_859";
}

} // namespace diag
