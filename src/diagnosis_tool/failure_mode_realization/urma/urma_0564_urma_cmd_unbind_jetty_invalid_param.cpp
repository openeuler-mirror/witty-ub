#include "urma_0564_urma_cmd_unbind_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0564UrmaCmdUnbindJettyInvalidParam> g_urma("urma_0564");

bool Urma0564UrmaCmdUnbindJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0564UrmaCmdUnbindJettyInvalidParam::GetName() const
{
    return "urma_cmd_unbind_jetty 参数非法";
}

std::string Urma0564UrmaCmdUnbindJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || jetty->urma_ctx == NULL || jetty->urma_ctx->dev_fd < 0 || "
           "jetty->remote_jetty == NU`；该路径返回 -1";
}

RootCause Urma0564UrmaCmdUnbindJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0564UrmaCmdUnbindJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0564UrmaCmdUnbindJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0564UrmaCmdUnbindJettyInvalidParam::GetId() const
{
    return "urma_0564";
}
} // namespace diag
