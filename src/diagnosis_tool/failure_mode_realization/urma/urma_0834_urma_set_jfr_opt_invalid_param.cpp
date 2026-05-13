#include "urma_0834_urma_set_jfr_opt_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0834UrmaSetJfrOptInvalidParam> g_urma("urma_0834");

bool Urma0834UrmaSetJfrOptInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0834UrmaSetJfrOptInvalidParam::GetName() const
{
    return "urma_set_jfr_opt 参数非法";
}

std::string Urma0834UrmaSetJfrOptInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL || buf == NULL || opt == 0 || len == 0`；该路径返回 URMA_EINVAL";
}

RootCause Urma0834UrmaSetJfrOptInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0834UrmaSetJfrOptInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0834UrmaSetJfrOptInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0834UrmaSetJfrOptInvalidParam::GetId() const
{
    return "urma_0834";
}
} // namespace diag
