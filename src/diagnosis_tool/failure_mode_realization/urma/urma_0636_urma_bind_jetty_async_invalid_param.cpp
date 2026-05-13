#include "urma_0636_urma_bind_jetty_async_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0636UrmaBindJettyAsyncInvalidParam> g_urma("urma_0636");

bool Urma0636UrmaBindJettyAsyncInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0636UrmaBindJettyAsyncInvalidParam::GetName() const
{
    return "urma_bind_jetty_async 参数非法";
}

std::string Urma0636UrmaBindJettyAsyncInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `notifier == NULL || jetty == NULL || tjetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0636UrmaBindJettyAsyncInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0636UrmaBindJettyAsyncInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0636UrmaBindJettyAsyncInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0636UrmaBindJettyAsyncInvalidParam::GetId() const
{
    return "urma_0636";
}
} // namespace diag
