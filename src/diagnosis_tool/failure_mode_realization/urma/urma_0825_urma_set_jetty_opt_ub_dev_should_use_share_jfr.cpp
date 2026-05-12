#include "urma_0825_urma_set_jetty_opt_ub_dev_should_use_share_jfr.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0825UrmaSetJettyOptUbDevShouldUseShareJfr> g_urma("urma_0825");

bool Urma0825UrmaSetJettyOptUbDevShouldUseShareJfr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"UB dev should use share jfr!"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0825UrmaSetJettyOptUbDevShouldUseShareJfr::GetName() const
{
    return "urma_set_jetty_opt UB dev should use share jfr!";
}

std::string Urma0825UrmaSetJettyOptUbDevShouldUseShareJfr::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `jetty->jetty_cfg.flag.bs.share_jfr == URMA_NO_SHARE_JFR && jetty->urma_ctx->dev->type "
           "== URMA_TRANSP`；该路径返回 URMA_EINVAL";
}

RootCause Urma0825UrmaSetJettyOptUbDevShouldUseShareJfr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0825UrmaSetJettyOptUbDevShouldUseShareJfr::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0825UrmaSetJettyOptUbDevShouldUseShareJfr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：UB dev should use share jfr!";
}

std::string Urma0825UrmaSetJettyOptUbDevShouldUseShareJfr::GetId() const
{
    return "urma_0825";
}
} // namespace diag
