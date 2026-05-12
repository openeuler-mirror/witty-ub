#include "urma_0077_bondp_add_jetty_p_vjetty_id_info_failed_add_p.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0077BondpAddJettyPVjettyIdInfoFailedAddP> g_urma("urma_0077");

bool Urma0077BondpAddJettyPVjettyIdInfoFailedAddP::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to add p_vjetty_id[%]: ret: %, p_jetty_id: %, v_jetty_id: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0077BondpAddJettyPVjettyIdInfoFailedAddP::GetName() const
{
    return "bondp_add_jetty_p_vjetty_id_info Failed to add p_vjetty_id[%]: ret: %";
}

std::string Urma0077BondpAddJettyPVjettyIdInfoFailedAddP::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret != 0`；该路径返回 0";
}

RootCause Urma0077BondpAddJettyPVjettyIdInfoFailedAddP::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0077BondpAddJettyPVjettyIdInfoFailedAddP::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0077BondpAddJettyPVjettyIdInfoFailedAddP::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to add p_vjetty_id[%]: ret: %, p_jetty_id: %, v_jetty_id: "
           "%";
}

std::string Urma0077BondpAddJettyPVjettyIdInfoFailedAddP::GetId() const
{
    return "urma_0077";
}
} // namespace diag
