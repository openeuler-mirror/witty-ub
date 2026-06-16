#include "urma_failure_727.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure727> g_urma("urma_727");

bool UrmaFailure727::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_user_ctl_set_bonding_mode' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid set bonding mode param.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure727::GetName() const
{
    return "URMA context无效导致设置context失败";
}

std::string UrmaFailure727::GetRootCauseDesc() const
{
    return "函数用于设置context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure727::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure727::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure727::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_user_ctl_set_bonding_mode，Invalid set bonding mode param.。";
}

std::string UrmaFailure727::GetId() const
{
    return "urma_727";
}

} // namespace diag
