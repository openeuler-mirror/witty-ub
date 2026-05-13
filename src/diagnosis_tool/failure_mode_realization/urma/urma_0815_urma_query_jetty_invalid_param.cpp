#include "urma_0815_urma_query_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0815UrmaQueryJettyInvalidParam> g_urma("urma_0815");

bool Urma0815UrmaQueryJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0815UrmaQueryJettyInvalidParam::GetName() const
{
    return "urma_query_jetty 参数非法";
}

std::string Urma0815UrmaQueryJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || cfg == NULL || attr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0815UrmaQueryJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0815UrmaQueryJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0815UrmaQueryJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0815UrmaQueryJettyInvalidParam::GetId() const
{
    return "urma_0815";
}
} // namespace diag
