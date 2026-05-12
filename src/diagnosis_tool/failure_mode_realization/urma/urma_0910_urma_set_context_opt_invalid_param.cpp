#include "urma_0910_urma_set_context_opt_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0910UrmaSetContextOptInvalidParam> g_urma("urma_0910");

bool Urma0910UrmaSetContextOptInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0910UrmaSetContextOptInvalidParam::GetName() const
{
    return "urma_set_context_opt 参数非法";
}

std::string Urma0910UrmaSetContextOptInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev == NULL || ctx->dev->ops == NULL`；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0910UrmaSetContextOptInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0910UrmaSetContextOptInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0910UrmaSetContextOptInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0910UrmaSetContextOptInvalidParam::GetId() const
{
    return "urma_0910";
}
} // namespace diag
