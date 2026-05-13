#include "urma_1221_urma_user_ctl_failed_excecute_user_ctl_ret.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1221UrmaUserCtlFailedExcecuteUserCtlRet> g_urma("urma_1221");

bool Urma1221UrmaUserCtlFailedExcecuteUserCtlRet::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to excecute user_ctl, ret: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1221UrmaUserCtlFailedExcecuteUserCtlRet::GetName() const
{
    return "urma_user_ctl Failed to excecute user_ctl, ret: %.";
}

std::string Urma1221UrmaUserCtlFailedExcecuteUserCtlRet::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `(urma_status_t)ret != URMA_SUCCESS && (urma_status_t)ret != URMA_ENOPERM`；该路径返回 "
           "URMA_FAIL";
}

RootCause Urma1221UrmaUserCtlFailedExcecuteUserCtlRet::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1221UrmaUserCtlFailedExcecuteUserCtlRet::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1221UrmaUserCtlFailedExcecuteUserCtlRet::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to excecute user_ctl, ret: %.";
}

std::string Urma1221UrmaUserCtlFailedExcecuteUserCtlRet::GetId() const
{
    return "urma_1221";
}
} // namespace diag
