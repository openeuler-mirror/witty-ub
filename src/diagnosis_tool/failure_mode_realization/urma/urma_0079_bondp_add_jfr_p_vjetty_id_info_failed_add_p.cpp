#include "urma_0079_bondp_add_jfr_p_vjetty_id_info_failed_add_p.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0079BondpAddJfrPVjettyIdInfoFailedAddP> g_urma("urma_0079");

bool Urma0079BondpAddJfrPVjettyIdInfoFailedAddP::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to add p_vjfr_id[%]: ret: %, p_jfr_id: %, v_jfr_id: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0079BondpAddJfrPVjettyIdInfoFailedAddP::GetName() const
{
    return "bondp_add_jfr_p_vjetty_id_info Failed to add p_vjfr_id[%]: ret: %,";
}

std::string Urma0079BondpAddJfrPVjettyIdInfoFailedAddP::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret`；该路径返回 0";
}

RootCause Urma0079BondpAddJfrPVjettyIdInfoFailedAddP::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0079BondpAddJfrPVjettyIdInfoFailedAddP::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0079BondpAddJfrPVjettyIdInfoFailedAddP::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to add p_vjfr_id[%]: ret: %, p_jfr_id: %, v_jfr_id: %";
}

std::string Urma0079BondpAddJfrPVjettyIdInfoFailedAddP::GetId() const
{
    return "urma_0079";
}
} // namespace diag
