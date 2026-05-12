#include "urma_0758_urma_free_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0758UrmaFreeJettyInvalidParam> g_urma("urma_0758");

bool Urma0758UrmaFreeJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0758UrmaFreeJettyInvalidParam::GetName() const
{
    return "urma_free_jetty 参数非法";
}

std::string Urma0758UrmaFreeJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0758UrmaFreeJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0758UrmaFreeJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0758UrmaFreeJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0758UrmaFreeJettyInvalidParam::GetId() const
{
    return "urma_0758";
}
} // namespace diag
