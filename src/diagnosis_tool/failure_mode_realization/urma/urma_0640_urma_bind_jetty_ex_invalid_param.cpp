#include "urma_0640_urma_bind_jetty_ex_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0640UrmaBindJettyExInvalidParam> g_urma("urma_0640");

bool Urma0640UrmaBindJettyExInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0640UrmaBindJettyExInvalidParam::GetName() const
{
    return "urma_bind_jetty_ex 参数非法";
}

std::string Urma0640UrmaBindJettyExInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || tjetty == NULL || cfg == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0640UrmaBindJettyExInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0640UrmaBindJettyExInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0640UrmaBindJettyExInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0640UrmaBindJettyExInvalidParam::GetId() const
{
    return "urma_0640";
}
} // namespace diag
