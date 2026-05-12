#include "urma_0632_urma_bind_jetty_invalid_param_ctx_null_ctx_dev_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0632UrmaBindJettyInvalidParamCtxNullCtxDevNull> g_urma("urma_0632");

bool Urma0632UrmaBindJettyInvalidParamCtxNullCtxDevNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0632UrmaBindJettyInvalidParamCtxNullCtxDevNull::GetName() const
{
    return "urma_bind_jetty 参数非法（ctx == NULL || ctx->dev == NULL || ctx->dev->sysfs_dev == NULL || ctx->ops == "
           "NULL）";
}

std::string Urma0632UrmaBindJettyInvalidParamCtxNullCtxDevNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev == NULL || ctx->dev->sysfs_dev == NULL || ctx->ops "
           "== NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0632UrmaBindJettyInvalidParamCtxNullCtxDevNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0632UrmaBindJettyInvalidParamCtxNullCtxDevNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0632UrmaBindJettyInvalidParamCtxNullCtxDevNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0632UrmaBindJettyInvalidParamCtxNullCtxDevNull::GetId() const
{
    return "urma_0632";
}
} // namespace diag
