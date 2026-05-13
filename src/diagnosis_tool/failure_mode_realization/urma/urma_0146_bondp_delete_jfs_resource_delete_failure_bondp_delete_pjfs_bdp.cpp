#include "urma_0146_bondp_delete_jfs_resource_delete_failure_bondp_delete_pjfs_bdp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0146BondpDeleteJfsResourceDeleteFailureBondpDeletePjfsBdp> g_urma("urma_0146");

bool Urma0146BondpDeleteJfsResourceDeleteFailureBondpDeletePjfsBdp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete pjfs"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0146BondpDeleteJfsResourceDeleteFailureBondpDeletePjfsBdp::GetName() const
{
    return "bondp_delete_jfs 删除资源失败（bondp_delete_pjfs(bdp_jfs) != URMA_SUCCESS）";
}

std::string Urma0146BondpDeleteJfsResourceDeleteFailureBondpDeletePjfsBdp::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0146BondpDeleteJfsResourceDeleteFailureBondpDeletePjfsBdp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0146BondpDeleteJfsResourceDeleteFailureBondpDeletePjfsBdp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0146BondpDeleteJfsResourceDeleteFailureBondpDeletePjfsBdp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete pjfs";
}

std::string Urma0146BondpDeleteJfsResourceDeleteFailureBondpDeletePjfsBdp::GetId() const
{
    return "urma_0146";
}
} // namespace diag
