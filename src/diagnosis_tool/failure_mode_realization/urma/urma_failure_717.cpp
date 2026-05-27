#include "urma_failure_717.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure717> g_urma("urma_717");

bool UrmaFailure717::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_user_ctl_set_bonding_mode_legacy' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | "
                                    "grep -F 'Invalid aggr mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure717::GetName() const
{
    return "URMA context无效导致设置context失败";
}

std::string UrmaFailure717::GetRootCauseDesc() const
{
    return "函数用于设置context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure717::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure717::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure717::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_user_ctl_set_bonding_mode_legacy，Invalid aggr mode:";
}

std::string UrmaFailure717::GetId() const
{
    return "urma_717";
}

} // namespace diag
