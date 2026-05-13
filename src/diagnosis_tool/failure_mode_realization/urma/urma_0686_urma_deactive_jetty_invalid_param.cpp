#include "urma_0686_urma_deactive_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0686UrmaDeactiveJettyInvalidParam> g_urma("urma_0686");

bool Urma0686UrmaDeactiveJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0686UrmaDeactiveJettyInvalidParam::GetName() const
{
    return "urma_deactive_jetty 参数非法";
}

std::string Urma0686UrmaDeactiveJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0686UrmaDeactiveJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0686UrmaDeactiveJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0686UrmaDeactiveJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0686UrmaDeactiveJettyInvalidParam::GetId() const
{
    return "urma_0686";
}
} // namespace diag
