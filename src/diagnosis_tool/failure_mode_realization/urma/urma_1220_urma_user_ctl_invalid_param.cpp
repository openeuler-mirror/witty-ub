#include "urma_1220_urma_user_ctl_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1220UrmaUserCtlInvalidParam> g_urma("urma_1220");

bool Urma1220UrmaUserCtlInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1220UrmaUserCtlInvalidParam::GetName() const
{
    return "urma_user_ctl 参数非法";
}

std::string Urma1220UrmaUserCtlInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `(ctx == NULL) || (in == NULL) || (out == NULL)`；该路径返回 URMA_EINVAL";
}

RootCause Urma1220UrmaUserCtlInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1220UrmaUserCtlInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1220UrmaUserCtlInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1220UrmaUserCtlInvalidParam::GetId() const
{
    return "urma_1220";
}
} // namespace diag
