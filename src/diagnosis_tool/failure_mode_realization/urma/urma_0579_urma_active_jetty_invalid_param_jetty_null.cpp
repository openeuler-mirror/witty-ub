#include "urma_0579_urma_active_jetty_invalid_param_jetty_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0579UrmaActiveJettyInvalidParamJettyNull> g_urma("urma_0579");

bool Urma0579UrmaActiveJettyInvalidParamJettyNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0579UrmaActiveJettyInvalidParamJettyNull::GetName() const
{
    return "urma_active_jetty 参数非法（jetty == NULL）";
}

std::string Urma0579UrmaActiveJettyInvalidParamJettyNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0579UrmaActiveJettyInvalidParamJettyNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0579UrmaActiveJettyInvalidParamJettyNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0579UrmaActiveJettyInvalidParamJettyNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0579UrmaActiveJettyInvalidParamJettyNull::GetId() const
{
    return "urma_0579";
}
} // namespace diag
