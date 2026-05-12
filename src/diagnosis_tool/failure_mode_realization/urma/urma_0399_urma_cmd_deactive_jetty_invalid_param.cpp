#include "urma_0399_urma_cmd_deactive_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0399UrmaCmdDeactiveJettyInvalidParam> g_urma("urma_0399");

bool Urma0399UrmaCmdDeactiveJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0399UrmaCmdDeactiveJettyInvalidParam::GetName() const
{
    return "urma_cmd_deactive_jetty 参数非法";
}

std::string Urma0399UrmaCmdDeactiveJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || jetty->urma_ctx == NULL || jetty->urma_ctx->dev_fd < "
           "0`；该路径返回 -1";
}

RootCause Urma0399UrmaCmdDeactiveJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0399UrmaCmdDeactiveJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0399UrmaCmdDeactiveJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0399UrmaCmdDeactiveJettyInvalidParam::GetId() const
{
    return "urma_0399";
}
} // namespace diag
