#include "urma_failure_821.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure821> g_urma("urma_821");

bool UrmaFailure821::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure821::GetName() const
{
    return "provider操作表、JFR对象无效导致去激活JFR失败";
}

std::string UrmaFailure821::GetRootCauseDesc() const
{
    return "函数用于去激活JFR，调用方传入的provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure821::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure821::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure821::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_deactive_jfr，Invalid parameter.";
}

std::string UrmaFailure821::GetId() const
{
    return "urma_821";
}

} // namespace diag
