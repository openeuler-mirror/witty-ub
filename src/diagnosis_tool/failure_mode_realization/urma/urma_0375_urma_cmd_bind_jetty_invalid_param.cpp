#include "urma_0375_urma_cmd_bind_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0375UrmaCmdBindJettyInvalidParam> g_urma("urma_0375");

bool Urma0375UrmaCmdBindJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0375UrmaCmdBindJettyInvalidParam::GetName() const
{
    return "urma_cmd_bind_jetty 参数非法";
}

std::string Urma0375UrmaCmdBindJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || jetty->urma_ctx == NULL || jetty->urma_ctx->dev_fd < 0 || "
           "tjetty == NULL`；该路径返回 EINVAL";
}

RootCause Urma0375UrmaCmdBindJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0375UrmaCmdBindJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0375UrmaCmdBindJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0375UrmaCmdBindJettyInvalidParam::GetId() const
{
    return "urma_0375";
}
} // namespace diag
