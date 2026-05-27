#include "urma_failure_417.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure417> g_urma("urma_417");

bool UrmaFailure417::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_user_ctl_query_port' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'The object does not belong to current context.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure417::GetName() const
{
    return "查询context过程中依赖步骤失败";
}

std::string UrmaFailure417::GetRootCauseDesc() const
{
    return "函数用于查询context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA"
           "操作失败。";
}

RootCause UrmaFailure417::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure417::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure417::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_user_ctl_query_port，The object does not belong to current "
           "context.。";
}

std::string UrmaFailure417::GetId() const
{
    return "urma_417";
}

} // namespace diag
