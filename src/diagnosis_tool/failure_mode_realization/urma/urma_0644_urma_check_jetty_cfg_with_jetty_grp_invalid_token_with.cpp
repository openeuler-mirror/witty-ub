#include "urma_0644_urma_check_jetty_cfg_with_jetty_grp_invalid_token_with.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0644UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith> g_urma("urma_0644");

bool Urma0644UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid token with share_jfr."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0644UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith::GetName() const
{
    return "urma_check_jetty_cfg_with_jetty_grp Invalid token with share_jfr.";
}

std::string Urma0644UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `cfg->jetty_grp->cfg.token_value.token != cfg->shared.jfr->jfr_cfg.token_value.token || "
           "cfg->jetty_gr`；该路径返回 -1";
}

RootCause Urma0644UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0644UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0644UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid token with share_jfr.";
}

std::string Urma0644UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith::GetId() const
{
    return "urma_0644";
}
} // namespace diag
