#include "urma_failure_416.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure416> g_urma("urma_416");

bool UrmaFailure416::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_user_ctl_query_port' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid jfr.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure416::GetName() const
{
    return "URMA context、JFR对象无效导致查询JFR失败";
}

std::string UrmaFailure416::GetRootCauseDesc() const
{
    return "函数用于查询JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure416::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure416::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure416::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_user_ctl_query_port，Invalid jfr.。";
}

std::string UrmaFailure416::GetId() const
{
    return "urma_416";
}

} // namespace diag
