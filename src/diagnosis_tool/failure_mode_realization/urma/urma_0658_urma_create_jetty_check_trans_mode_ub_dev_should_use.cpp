#include "urma_0658_urma_create_jetty_check_trans_mode_ub_dev_should_use.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0658UrmaCreateJettyCheckTransModeUbDevShouldUse> g_urma("urma_0658");

bool Urma0658UrmaCreateJettyCheckTransModeUbDevShouldUse::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"UB dev should use share jfr!"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0658UrmaCreateJettyCheckTransModeUbDevShouldUse::GetName() const
{
    return "urma_create_jetty_check_trans_mode UB dev should use share jfr!";
}

std::string Urma0658UrmaCreateJettyCheckTransModeUbDevShouldUse::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `jetty_cfg->flag.bs.share_jfr == URMA_NO_SHARE_JFR && ctx->dev->type == "
           "URMA_TRANSPORT_UB`；该路径返回 -1";
}

RootCause Urma0658UrmaCreateJettyCheckTransModeUbDevShouldUse::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0658UrmaCreateJettyCheckTransModeUbDevShouldUse::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0658UrmaCreateJettyCheckTransModeUbDevShouldUse::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：UB dev should use share jfr!";
}

std::string Urma0658UrmaCreateJettyCheckTransModeUbDevShouldUse::GetId() const
{
    return "urma_0658";
}
} // namespace diag
