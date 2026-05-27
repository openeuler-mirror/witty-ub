#include "urma_failure_412.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure412> g_urma("urma_412");

bool UrmaFailure412::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_user_ctl_query_port' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid jfr.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure412::GetName() const
{
    return "URMA context、JFR对象无效导致查询JFR失败";
}

std::string UrmaFailure412::GetRootCauseDesc() const
{
    return "函数用于查询JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure412::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure412::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure412::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_user_ctl_query_port，Invalid jfr.";
}

std::string UrmaFailure412::GetId() const
{
    return "urma_412";
}

} // namespace diag
