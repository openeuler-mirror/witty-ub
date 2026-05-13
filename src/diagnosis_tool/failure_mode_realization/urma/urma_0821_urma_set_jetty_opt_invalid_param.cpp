#include "urma_0821_urma_set_jetty_opt_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0821UrmaSetJettyOptInvalidParam> g_urma("urma_0821");

bool Urma0821UrmaSetJettyOptInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0821UrmaSetJettyOptInvalidParam::GetName() const
{
    return "urma_set_jetty_opt 参数非法";
}

std::string Urma0821UrmaSetJettyOptInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || buf == NULL || opt == 0 || len == 0`；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0821UrmaSetJettyOptInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0821UrmaSetJettyOptInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0821UrmaSetJettyOptInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0821UrmaSetJettyOptInvalidParam::GetId() const
{
    return "urma_0821";
}
} // namespace diag
