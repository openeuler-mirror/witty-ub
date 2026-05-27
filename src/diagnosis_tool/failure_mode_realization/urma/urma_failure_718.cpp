#include "urma_failure_718.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure718> g_urma("urma_718");

bool UrmaFailure718::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_user_ctl_set_bonding_mode' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid set bonding mode param.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure718::GetName() const
{
    return "URMA context无效导致设置context失败";
}

std::string UrmaFailure718::GetRootCauseDesc() const
{
    return "函数用于设置context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure718::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure718::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure718::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_user_ctl_set_bonding_mode，Invalid set bonding mode param.";
}

std::string UrmaFailure718::GetId() const
{
    return "urma_718";
}

} // namespace diag
