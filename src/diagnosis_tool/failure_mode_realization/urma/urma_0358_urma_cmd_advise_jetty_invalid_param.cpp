#include "urma_0358_urma_cmd_advise_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0358UrmaCmdAdviseJettyInvalidParam> g_urma("urma_0358");

bool Urma0358UrmaCmdAdviseJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0358UrmaCmdAdviseJettyInvalidParam::GetName() const
{
    return "urma_cmd_advise_jetty 参数非法";
}

std::string Urma0358UrmaCmdAdviseJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || jetty->urma_ctx == NULL || jetty->urma_ctx->dev_fd < 0 || "
           "tjetty == NULL`；该路径返回 -1";
}

RootCause Urma0358UrmaCmdAdviseJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0358UrmaCmdAdviseJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0358UrmaCmdAdviseJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0358UrmaCmdAdviseJettyInvalidParam::GetId() const
{
    return "urma_0358";
}
} // namespace diag
