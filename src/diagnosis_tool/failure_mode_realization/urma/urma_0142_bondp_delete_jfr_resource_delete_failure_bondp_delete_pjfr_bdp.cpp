#include "urma_0142_bondp_delete_jfr_resource_delete_failure_bondp_delete_pjfr_bdp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0142BondpDeleteJfrResourceDeleteFailureBondpDeletePjfrBdp> g_urma("urma_0142");

bool Urma0142BondpDeleteJfrResourceDeleteFailureBondpDeletePjfrBdp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete pjfr"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0142BondpDeleteJfrResourceDeleteFailureBondpDeletePjfrBdp::GetName() const
{
    return "bondp_delete_jfr 删除资源失败（bondp_delete_pjfr(bdp_jfr) != URMA_SUCCESS）";
}

std::string Urma0142BondpDeleteJfrResourceDeleteFailureBondpDeletePjfrBdp::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "ret";
}

RootCause Urma0142BondpDeleteJfrResourceDeleteFailureBondpDeletePjfrBdp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0142BondpDeleteJfrResourceDeleteFailureBondpDeletePjfrBdp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0142BondpDeleteJfrResourceDeleteFailureBondpDeletePjfrBdp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete pjfr";
}

std::string Urma0142BondpDeleteJfrResourceDeleteFailureBondpDeletePjfrBdp::GetId() const
{
    return "urma_0142";
}
} // namespace diag
