#include "urma_0110_bondp_create_jfs_failed_add_jfs_p_vjetty_id_info.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0110BondpCreateJfsFailedAddJfsPVjettyIdInfo> g_urma("urma_0110");

bool Urma0110BondpCreateJfsFailedAddJfsPVjettyIdInfo::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to add jfs p_vjetty_id info"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0110BondpCreateJfsFailedAddJfsPVjettyIdInfo::GetName() const
{
    return "bondp_create_jfs Failed to add jfs p_vjetty_id info";
}

std::string Urma0110BondpCreateJfsFailedAddJfsPVjettyIdInfo::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bondp_add_jfs_p_vjetty_id_info(bdp_ctx, bdp_jfs, bdp_jfs->v_jfs.jfs_id.id)`";
}

RootCause Urma0110BondpCreateJfsFailedAddJfsPVjettyIdInfo::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0110BondpCreateJfsFailedAddJfsPVjettyIdInfo::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0110BondpCreateJfsFailedAddJfsPVjettyIdInfo::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to add jfs p_vjetty_id info";
}

std::string Urma0110BondpCreateJfsFailedAddJfsPVjettyIdInfo::GetId() const
{
    return "urma_0110";
}
} // namespace diag
