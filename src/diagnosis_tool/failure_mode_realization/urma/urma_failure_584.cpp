#include "urma_failure_584.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure584> g_urma("urma_584");

bool UrmaFailure584::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_send' \"$URMA_LOG_PATH\" 2>/dev/null "
                                    "| grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure584::GetName() const
{
    return "JFS对象无效导致获取JFR失败";
}

std::string UrmaFailure584::GetRootCauseDesc() const
{
    return "函数用于获取JFR，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure584::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure584::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure584::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_send，Invalid parameter.。";
}

std::string UrmaFailure584::GetId() const
{
    return "urma_584";
}

} // namespace diag
