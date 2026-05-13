#include "urma_0141_bondp_delete_jfr_resource_delete_failure_bondp_delete_vjfr_bdp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0141BondpDeleteJfrResourceDeleteFailureBondpDeleteVjfrBdp> g_urma("urma_0141");

bool Urma0141BondpDeleteJfrResourceDeleteFailureBondpDeleteVjfrBdp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete_vjfr"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0141BondpDeleteJfrResourceDeleteFailureBondpDeleteVjfrBdp::GetName() const
{
    return "bondp_delete_jfr 删除资源失败（bondp_delete_vjfr(bdp_jfr) != URMA_SUCCESS）";
}

std::string Urma0141BondpDeleteJfrResourceDeleteFailureBondpDeleteVjfrBdp::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0141BondpDeleteJfrResourceDeleteFailureBondpDeleteVjfrBdp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0141BondpDeleteJfrResourceDeleteFailureBondpDeleteVjfrBdp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0141BondpDeleteJfrResourceDeleteFailureBondpDeleteVjfrBdp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete_vjfr";
}

std::string Urma0141BondpDeleteJfrResourceDeleteFailureBondpDeleteVjfrBdp::GetId() const
{
    return "urma_0141";
}
} // namespace diag
