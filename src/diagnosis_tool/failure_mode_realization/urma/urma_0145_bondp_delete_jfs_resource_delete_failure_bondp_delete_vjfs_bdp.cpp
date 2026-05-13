#include "urma_0145_bondp_delete_jfs_resource_delete_failure_bondp_delete_vjfs_bdp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0145BondpDeleteJfsResourceDeleteFailureBondpDeleteVjfsBdp> g_urma("urma_0145");

bool Urma0145BondpDeleteJfsResourceDeleteFailureBondpDeleteVjfsBdp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete vjfs"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0145BondpDeleteJfsResourceDeleteFailureBondpDeleteVjfsBdp::GetName() const
{
    return "bondp_delete_jfs 删除资源失败（bondp_delete_vjfs(bdp_jfs) != URMA_SUCCESS）";
}

std::string Urma0145BondpDeleteJfsResourceDeleteFailureBondpDeleteVjfsBdp::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0145BondpDeleteJfsResourceDeleteFailureBondpDeleteVjfsBdp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0145BondpDeleteJfsResourceDeleteFailureBondpDeleteVjfsBdp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0145BondpDeleteJfsResourceDeleteFailureBondpDeleteVjfsBdp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete vjfs";
}

std::string Urma0145BondpDeleteJfsResourceDeleteFailureBondpDeleteVjfsBdp::GetId() const
{
    return "urma_0145";
}
} // namespace diag
