#include "urma_0525_urma_cmd_query_jetty_invalid_param_jetty_null_jetty_urma.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0525UrmaCmdQueryJettyInvalidParamJettyNullJettyUrma> g_urma("urma_0525");

bool Urma0525UrmaCmdQueryJettyInvalidParamJettyNullJettyUrma::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0525UrmaCmdQueryJettyInvalidParamJettyNullJettyUrma::GetName() const
{
    return "urma_cmd_query_jetty 参数非法（jetty == NULL || jetty->urma_ctx == NULL || jetty->urma_ctx->dev_fd < 0 || "
           "cfg == NULL || attr == NU）";
}

std::string Urma0525UrmaCmdQueryJettyInvalidParamJettyNullJettyUrma::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || jetty->urma_ctx == NULL || jetty->urma_ctx->dev_fd < 0 || "
           "cfg == NULL || attr == NU`；该路径返回 -1";
}

RootCause Urma0525UrmaCmdQueryJettyInvalidParamJettyNullJettyUrma::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0525UrmaCmdQueryJettyInvalidParamJettyNullJettyUrma::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0525UrmaCmdQueryJettyInvalidParamJettyNullJettyUrma::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0525UrmaCmdQueryJettyInvalidParamJettyNullJettyUrma::GetId() const
{
    return "urma_0525";
}
} // namespace diag
