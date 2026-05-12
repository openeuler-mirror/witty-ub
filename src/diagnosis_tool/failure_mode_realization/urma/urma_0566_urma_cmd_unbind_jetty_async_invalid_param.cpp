#include "urma_0566_urma_cmd_unbind_jetty_async_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0566UrmaCmdUnbindJettyAsyncInvalidParam> g_urma("urma_0566");

bool Urma0566UrmaCmdUnbindJettyAsyncInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0566UrmaCmdUnbindJettyAsyncInvalidParam::GetName() const
{
    return "urma_cmd_unbind_jetty_async 参数非法";
}

std::string Urma0566UrmaCmdUnbindJettyAsyncInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || jetty->urma_ctx == NULL || jetty->urma_ctx->dev_fd < 0 || "
           "jetty->remote_jetty == NU`；该路径返回 -1";
}

RootCause Urma0566UrmaCmdUnbindJettyAsyncInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0566UrmaCmdUnbindJettyAsyncInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0566UrmaCmdUnbindJettyAsyncInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0566UrmaCmdUnbindJettyAsyncInvalidParam::GetId() const
{
    return "urma_0566";
}
} // namespace diag
