#include "urma_0126_bondp_del_jfr_p_vjetty_info_without_lock_resource_delete.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0126BondpDelJfrPVjettyInfoWithoutLockResourceDelete> g_urma("urma_0126");

bool Urma0126BondpDelJfrPVjettyInfoWithoutLockResourceDelete::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete p_vjfr_id node[%]: ret % pjfr_id: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0126BondpDelJfrPVjettyInfoWithoutLockResourceDelete::GetName() const
{
    return "bondp_del_jfr_p_vjetty_info_without_lock 删除资源失败";
}

std::string Urma0126BondpDelJfrPVjettyInfoWithoutLockResourceDelete::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0126BondpDelJfrPVjettyInfoWithoutLockResourceDelete::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0126BondpDelJfrPVjettyInfoWithoutLockResourceDelete::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0126BondpDelJfrPVjettyInfoWithoutLockResourceDelete::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete p_vjfr_id node[%]: ret % pjfr_id: %";
}

std::string Urma0126BondpDelJfrPVjettyInfoWithoutLockResourceDelete::GetId() const
{
    return "urma_0126";
}
} // namespace diag
