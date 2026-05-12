#include "urma_0473_urma_cmd_get_jetty_opt_invalid_param_jetty_null_buf.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0473UrmaCmdGetJettyOptInvalidParamJettyNullBuf> g_urma("urma_0473");

bool Urma0473UrmaCmdGetJettyOptInvalidParamJettyNullBuf::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0473UrmaCmdGetJettyOptInvalidParamJettyNullBuf::GetName() const
{
    return "urma_cmd_get_jetty_opt 参数非法（jetty == NULL || buf == NULL || opt == 0 || len == 0）";
}

std::string Urma0473UrmaCmdGetJettyOptInvalidParamJettyNullBuf::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || buf == NULL || opt == 0 || len == 0`；该路径返回 -1";
}

RootCause Urma0473UrmaCmdGetJettyOptInvalidParamJettyNullBuf::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0473UrmaCmdGetJettyOptInvalidParamJettyNullBuf::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0473UrmaCmdGetJettyOptInvalidParamJettyNullBuf::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0473UrmaCmdGetJettyOptInvalidParamJettyNullBuf::GetId() const
{
    return "urma_0473";
}
} // namespace diag
