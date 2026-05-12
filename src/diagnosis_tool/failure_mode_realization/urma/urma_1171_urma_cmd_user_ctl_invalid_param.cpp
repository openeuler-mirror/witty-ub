#include "urma_1171_urma_cmd_user_ctl_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1171UrmaCmdUserCtlInvalidParam> g_urma("urma_1171");

bool Urma1171UrmaCmdUserCtlInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1171UrmaCmdUserCtlInvalidParam::GetName() const
{
    return "urma_cmd_user_ctl 参数非法";
}

std::string Urma1171UrmaCmdUserCtlInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || in == NULL || out == NULL`；该路径返回 -EINVAL";
}

RootCause Urma1171UrmaCmdUserCtlInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1171UrmaCmdUserCtlInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1171UrmaCmdUserCtlInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1171UrmaCmdUserCtlInvalidParam::GetId() const
{
    return "urma_1171";
}
} // namespace diag
