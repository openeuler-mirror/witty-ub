#include "urma_failure_574.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure574> g_urma("urma_574");

bool UrmaFailure574::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'check_valid_jfr_wr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'There are invalid parameters.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure574::GetName() const
{
    return "JFR对象、WR对象无效导致执行JFR失败";
}

std::string UrmaFailure574::GetRootCauseDesc() const
{
    return "函数用于执行JFR，调用方传入的JFR对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure574::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure574::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure574::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：check_valid_jfr_wr，There are invalid parameters.";
}

std::string UrmaFailure574::GetId() const
{
    return "urma_574";
}

} // namespace diag
