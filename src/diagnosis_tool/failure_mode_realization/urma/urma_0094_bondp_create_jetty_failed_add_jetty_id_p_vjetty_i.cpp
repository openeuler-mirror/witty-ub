#include "urma_0094_bondp_create_jetty_failed_add_jetty_id_p_vjetty_i.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0094BondpCreateJettyFailedAddJettyIdPVjettyI> g_urma("urma_0094");

bool Urma0094BondpCreateJettyFailedAddJettyIdPVjettyI::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to add jetty id to p_vjetty_id table"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0094BondpCreateJettyFailedAddJettyIdPVjettyI::GetName() const
{
    return "bondp_create_jetty Failed to add jetty id to p_vjetty_i";
}

std::string Urma0094BondpCreateJettyFailedAddJettyIdPVjettyI::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bondp_add_jetty_p_vjetty_id_info(bdp_ctx, bdp_jetty, bdp_jetty->v_jetty.jetty_id.id) "
           "!= 0`";
}

RootCause Urma0094BondpCreateJettyFailedAddJettyIdPVjettyI::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0094BondpCreateJettyFailedAddJettyIdPVjettyI::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0094BondpCreateJettyFailedAddJettyIdPVjettyI::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to add jetty id to p_vjetty_id table";
}

std::string Urma0094BondpCreateJettyFailedAddJettyIdPVjettyI::GetId() const
{
    return "urma_0094";
}
} // namespace diag
