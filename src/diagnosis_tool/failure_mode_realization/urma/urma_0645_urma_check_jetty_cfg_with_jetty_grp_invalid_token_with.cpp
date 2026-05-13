#include "urma_0645_urma_check_jetty_cfg_with_jetty_grp_invalid_token_with.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0645UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith> g_urma("urma_0645");

bool Urma0645UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid token with unshared jfr."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0645UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith::GetName() const
{
    return "urma_check_jetty_cfg_with_jetty_grp Invalid token with unshared jfr.";
}

std::string Urma0645UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `cfg->jetty_grp->cfg.token_value.token != cfg->jfr_cfg->token_value.token || "
           "cfg->jetty_grp->cfg.flag`；该路径返回 -1";
}

RootCause Urma0645UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0645UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0645UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid token with unshared jfr.";
}

std::string Urma0645UrmaCheckJettyCfgWithJettyGrpInvalidTokenWith::GetId() const
{
    return "urma_0645";
}
} // namespace diag
