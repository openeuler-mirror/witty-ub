#include "urma_0377_urma_cmd_bind_jetty_async_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0377UrmaCmdBindJettyAsyncInvalidParam> g_urma("urma_0377");

bool Urma0377UrmaCmdBindJettyAsyncInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0377UrmaCmdBindJettyAsyncInvalidParam::GetName() const
{
    return "urma_cmd_bind_jetty_async 参数非法";
}

std::string Urma0377UrmaCmdBindJettyAsyncInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `notifier == NULL || jetty == NULL || jetty->urma_ctx == NULL || "
           "jetty->urma_ctx->dev_fd < 0 || tjett`；该路径返回 EINVAL";
}

RootCause Urma0377UrmaCmdBindJettyAsyncInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0377UrmaCmdBindJettyAsyncInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0377UrmaCmdBindJettyAsyncInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0377UrmaCmdBindJettyAsyncInvalidParam::GetId() const
{
    return "urma_0377";
}
} // namespace diag
