#include "urma_0415_urma_cmd_delete_jetty_batch_invalid_param_jetty_null_jetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0415UrmaCmdDeleteJettyBatchInvalidParamJettyNullJetty> g_urma("urma_0415");

bool Urma0415UrmaCmdDeleteJettyBatchInvalidParamJettyNullJetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, index: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0415UrmaCmdDeleteJettyBatchInvalidParamJettyNullJetty::GetName() const
{
    return "urma_cmd_delete_jetty_batch 参数非法（jetty == NULL || jetty->urma_ctx == NULL）";
}

std::string Urma0415UrmaCmdDeleteJettyBatchInvalidParamJettyNullJetty::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || jetty->urma_ctx == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0415UrmaCmdDeleteJettyBatchInvalidParamJettyNullJetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0415UrmaCmdDeleteJettyBatchInvalidParamJettyNullJetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0415UrmaCmdDeleteJettyBatchInvalidParamJettyNullJetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, index: %.";
}

std::string Urma0415UrmaCmdDeleteJettyBatchInvalidParamJettyNullJetty::GetId() const
{
    return "urma_0415";
}
} // namespace diag
