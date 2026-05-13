#include "urma_0647_urma_create_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0647UrmaCreateJettyInvalidParam> g_urma("urma_0647");

bool Urma0647UrmaCreateJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0647UrmaCreateJettyInvalidParam::GetName() const
{
    return "urma_create_jetty 参数非法";
}

std::string Urma0647UrmaCreateJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || jetty_cfg == NULL || ctx->dev == NULL`；该路径返回 NULL";
}

RootCause Urma0647UrmaCreateJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0647UrmaCreateJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0647UrmaCreateJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0647UrmaCreateJettyInvalidParam::GetId() const
{
    return "urma_0647";
}
} // namespace diag
