#include "urma_0702_urma_delete_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0702UrmaDeleteJettyInvalidParam> g_urma("urma_0702");

bool Urma0702UrmaDeleteJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0702UrmaDeleteJettyInvalidParam::GetName() const
{
    return "urma_delete_jetty 参数非法";
}

std::string Urma0702UrmaDeleteJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0702UrmaDeleteJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0702UrmaDeleteJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0702UrmaDeleteJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0702UrmaDeleteJettyInvalidParam::GetId() const
{
    return "urma_0702";
}
} // namespace diag
