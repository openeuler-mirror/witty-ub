#include "urma_failure_839.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure839> g_urma("urma_839");

bool UrmaFailure839::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unadvise_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure839::GetName() const
{
    return "URMA context、provider操作表、JFS对象无效导致执行JFR失败";
}

std::string UrmaFailure839::GetRootCauseDesc() const
{
    return "函数用于执行JFR，调用方传入的URMA "
           "context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure839::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure839::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure839::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_unadvise_jfr，Invalid parameter.";
}

std::string UrmaFailure839::GetId() const
{
    return "urma_839";
}

} // namespace diag
