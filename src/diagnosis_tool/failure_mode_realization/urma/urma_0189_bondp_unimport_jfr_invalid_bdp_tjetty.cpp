#include "urma_0189_bondp_unimport_jfr_invalid_bdp_tjetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0189BondpUnimportJfrInvalidBdpTjetty> g_urma("urma_0189");

bool Urma0189BondpUnimportJfrInvalidBdpTjetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid bdp tjetty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0189BondpUnimportJfrInvalidBdpTjetty::GetName() const
{
    return "bondp_unimport_jfr Invalid bdp tjetty";
}

std::string Urma0189BondpUnimportJfrInvalidBdpTjetty::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bdp_tjetty(bdp_tjetty)`；该路径返回 URMA_EINVAL";
}

RootCause Urma0189BondpUnimportJfrInvalidBdpTjetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0189BondpUnimportJfrInvalidBdpTjetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0189BondpUnimportJfrInvalidBdpTjetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid bdp tjetty";
}

std::string Urma0189BondpUnimportJfrInvalidBdpTjetty::GetId() const
{
    return "urma_0189";
}
} // namespace diag
