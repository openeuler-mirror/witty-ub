#include "urma_0852_urma_unbind_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0852UrmaUnbindJettyInvalidParam> g_urma("urma_0852");

bool Urma0852UrmaUnbindJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0852UrmaUnbindJettyInvalidParam::GetName() const
{
    return "urma_unbind_jetty 参数非法";
}

std::string Urma0852UrmaUnbindJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || jetty->remote_jetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0852UrmaUnbindJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0852UrmaUnbindJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0852UrmaUnbindJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0852UrmaUnbindJettyInvalidParam::GetId() const
{
    return "urma_0852";
}
} // namespace diag
