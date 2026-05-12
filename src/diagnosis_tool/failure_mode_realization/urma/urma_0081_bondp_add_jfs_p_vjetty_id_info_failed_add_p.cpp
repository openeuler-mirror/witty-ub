#include "urma_0081_bondp_add_jfs_p_vjetty_id_info_failed_add_p.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0081BondpAddJfsPVjettyIdInfoFailedAddP> g_urma("urma_0081");

bool Urma0081BondpAddJfsPVjettyIdInfoFailedAddP::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to add p_vjfs_id[%]: ret: %, p_jfs_id: %, v_jfs_id: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0081BondpAddJfsPVjettyIdInfoFailedAddP::GetName() const
{
    return "bondp_add_jfs_p_vjetty_id_info Failed to add p_vjfs_id[%]: ret: %,";
}

std::string Urma0081BondpAddJfsPVjettyIdInfoFailedAddP::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret`；该路径返回 0";
}

RootCause Urma0081BondpAddJfsPVjettyIdInfoFailedAddP::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0081BondpAddJfsPVjettyIdInfoFailedAddP::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0081BondpAddJfsPVjettyIdInfoFailedAddP::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to add p_vjfs_id[%]: ret: %, p_jfs_id: %, v_jfs_id: %";
}

std::string Urma0081BondpAddJfsPVjettyIdInfoFailedAddP::GetId() const
{
    return "urma_0081";
}
} // namespace diag
