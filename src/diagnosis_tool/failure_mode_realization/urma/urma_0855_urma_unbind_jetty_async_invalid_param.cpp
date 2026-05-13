#include "urma_0855_urma_unbind_jetty_async_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0855UrmaUnbindJettyAsyncInvalidParam> g_urma("urma_0855");

bool Urma0855UrmaUnbindJettyAsyncInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0855UrmaUnbindJettyAsyncInvalidParam::GetName() const
{
    return "urma_unbind_jetty_async 参数非法";
}

std::string Urma0855UrmaUnbindJettyAsyncInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || jetty->remote_jetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0855UrmaUnbindJettyAsyncInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0855UrmaUnbindJettyAsyncInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0855UrmaUnbindJettyAsyncInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0855UrmaUnbindJettyAsyncInvalidParam::GetId() const
{
    return "urma_0855";
}
} // namespace diag
