#include "urma_0132_bondp_delete_jetty_resource_delete_failure_bondp_delete_pjetty_bdp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0132BondpDeleteJettyResourceDeleteFailureBondpDeletePjettyBdp> g_urma("urma_0132");

bool Urma0132BondpDeleteJettyResourceDeleteFailureBondpDeletePjettyBdp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete pjetty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0132BondpDeleteJettyResourceDeleteFailureBondpDeletePjettyBdp::GetName() const
{
    return "bondp_delete_jetty 删除资源失败（bondp_delete_pjetty(bdp_jetty) != URMA_SUCCESS）";
}

std::string Urma0132BondpDeleteJettyResourceDeleteFailureBondpDeletePjettyBdp::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0132BondpDeleteJettyResourceDeleteFailureBondpDeletePjettyBdp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0132BondpDeleteJettyResourceDeleteFailureBondpDeletePjettyBdp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0132BondpDeleteJettyResourceDeleteFailureBondpDeletePjettyBdp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete pjetty";
}

std::string Urma0132BondpDeleteJettyResourceDeleteFailureBondpDeletePjettyBdp::GetId() const
{
    return "urma_0132";
}
} // namespace diag
