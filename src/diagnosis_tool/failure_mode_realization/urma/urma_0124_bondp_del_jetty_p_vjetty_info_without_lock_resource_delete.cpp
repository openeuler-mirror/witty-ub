#include "urma_0124_bondp_del_jetty_p_vjetty_info_without_lock_resource_delete.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0124BondpDelJettyPVjettyInfoWithoutLockResourceDelete> g_urma("urma_0124");

bool Urma0124BondpDelJettyPVjettyInfoWithoutLockResourceDelete::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete p_vjetty_id node: ret: % pjetty_id: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0124BondpDelJettyPVjettyInfoWithoutLockResourceDelete::GetName() const
{
    return "bondp_del_jetty_p_vjetty_info_without_lock 删除资源失败";
}

std::string Urma0124BondpDelJettyPVjettyInfoWithoutLockResourceDelete::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0124BondpDelJettyPVjettyInfoWithoutLockResourceDelete::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0124BondpDelJettyPVjettyInfoWithoutLockResourceDelete::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0124BondpDelJettyPVjettyInfoWithoutLockResourceDelete::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete p_vjetty_id node: ret: % pjetty_id: %";
}

std::string Urma0124BondpDelJettyPVjettyInfoWithoutLockResourceDelete::GetId() const
{
    return "urma_0124";
}
} // namespace diag
