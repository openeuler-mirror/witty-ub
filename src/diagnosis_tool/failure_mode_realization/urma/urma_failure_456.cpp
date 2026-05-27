#include "urma_failure_456.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure456> g_urma("urma_456");

bool UrmaFailure456::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_jfr_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure456::GetName() const
{
    return "provider操作表、JFR对象无效导致获取JFR失败";
}

std::string UrmaFailure456::GetRootCauseDesc() const
{
    return "函数用于获取JFR，调用方传入的provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure456::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure456::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure456::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_get_jfr_opt，Invalid parameter.";
}

std::string UrmaFailure456::GetId() const
{
    return "urma_456";
}

} // namespace diag
