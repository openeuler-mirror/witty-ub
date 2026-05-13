#include "urma_0474_urma_cmd_get_jetty_opt_invalid_param_ctx_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0474UrmaCmdGetJettyOptInvalidParamCtxNull> g_urma("urma_0474");

bool Urma0474UrmaCmdGetJettyOptInvalidParamCtxNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0474UrmaCmdGetJettyOptInvalidParamCtxNull::GetName() const
{
    return "urma_cmd_get_jetty_opt 参数非法（ctx == NULL）";
}

std::string Urma0474UrmaCmdGetJettyOptInvalidParamCtxNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL`；该路径返回 -1";
}

RootCause Urma0474UrmaCmdGetJettyOptInvalidParamCtxNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0474UrmaCmdGetJettyOptInvalidParamCtxNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0474UrmaCmdGetJettyOptInvalidParamCtxNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0474UrmaCmdGetJettyOptInvalidParamCtxNull::GetId() const
{
    return "urma_0474";
}
} // namespace diag
