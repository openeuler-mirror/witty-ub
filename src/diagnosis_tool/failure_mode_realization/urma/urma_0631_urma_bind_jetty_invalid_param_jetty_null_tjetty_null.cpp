#include "urma_0631_urma_bind_jetty_invalid_param_jetty_null_tjetty_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0631UrmaBindJettyInvalidParamJettyNullTjettyNull> g_urma("urma_0631");

bool Urma0631UrmaBindJettyInvalidParamJettyNullTjettyNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0631UrmaBindJettyInvalidParamJettyNullTjettyNull::GetName() const
{
    return "urma_bind_jetty 参数非法（jetty == NULL || tjetty == NULL）";
}

std::string Urma0631UrmaBindJettyInvalidParamJettyNullTjettyNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || tjetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0631UrmaBindJettyInvalidParamJettyNullTjettyNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0631UrmaBindJettyInvalidParamJettyNullTjettyNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0631UrmaBindJettyInvalidParamJettyNullTjettyNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0631UrmaBindJettyInvalidParamJettyNullTjettyNull::GetId() const
{
    return "urma_0631";
}
} // namespace diag
