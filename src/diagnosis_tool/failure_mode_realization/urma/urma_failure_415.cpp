#include "urma_failure_415.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure415> g_urma("urma_415");

bool UrmaFailure415::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_user_ctl_query_port' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid query port param.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure415::GetName() const
{
    return "URMA context无效导致查询端口失败";
}

std::string UrmaFailure415::GetRootCauseDesc() const
{
    return "函数用于查询端口，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure415::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure415::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure415::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_user_ctl_query_port，Invalid query port param.。";
}

std::string UrmaFailure415::GetId() const
{
    return "urma_415";
}

} // namespace diag
