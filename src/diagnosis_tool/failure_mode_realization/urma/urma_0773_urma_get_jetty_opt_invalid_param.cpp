#include "urma_0773_urma_get_jetty_opt_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0773UrmaGetJettyOptInvalidParam> g_urma("urma_0773");

bool Urma0773UrmaGetJettyOptInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0773UrmaGetJettyOptInvalidParam::GetName() const
{
    return "urma_get_jetty_opt 参数非法";
}

std::string Urma0773UrmaGetJettyOptInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || buf == NULL || opt == 0 || len == 0`；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0773UrmaGetJettyOptInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0773UrmaGetJettyOptInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0773UrmaGetJettyOptInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0773UrmaGetJettyOptInvalidParam::GetId() const
{
    return "urma_0773";
}
} // namespace diag
