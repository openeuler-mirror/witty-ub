#include "urma_0135_bondp_delete_jfc_resource_delete_failure_bondp_delete_vjfc_bdp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0135BondpDeleteJfcResourceDeleteFailureBondpDeleteVjfcBdp> g_urma("urma_0135");

bool Urma0135BondpDeleteJfcResourceDeleteFailureBondpDeleteVjfcBdp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete vjfc"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0135BondpDeleteJfcResourceDeleteFailureBondpDeleteVjfcBdp::GetName() const
{
    return "bondp_delete_jfc 删除资源失败（bondp_delete_vjfc(bdp_jfc) != URMA_SUCCESS）";
}

std::string Urma0135BondpDeleteJfcResourceDeleteFailureBondpDeleteVjfcBdp::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0135BondpDeleteJfcResourceDeleteFailureBondpDeleteVjfcBdp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0135BondpDeleteJfcResourceDeleteFailureBondpDeleteVjfcBdp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0135BondpDeleteJfcResourceDeleteFailureBondpDeleteVjfcBdp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete vjfc";
}

std::string Urma0135BondpDeleteJfcResourceDeleteFailureBondpDeleteVjfcBdp::GetId() const
{
    return "urma_0135";
}
} // namespace diag
