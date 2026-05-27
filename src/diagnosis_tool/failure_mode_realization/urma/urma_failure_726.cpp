#include "urma_failure_726.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure726> g_urma("urma_726");

bool UrmaFailure726::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_user_ctl_set_bonding_mode_legacy' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid aggr mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure726::GetName() const
{
    return "URMA context无效导致设置context失败";
}

std::string UrmaFailure726::GetRootCauseDesc() const
{
    return "函数用于设置context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure726::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure726::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure726::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_user_ctl_set_bonding_mode_legacy，Invalid aggr mode:。";
}

std::string UrmaFailure726::GetId() const
{
    return "urma_726";
}

} // namespace diag
