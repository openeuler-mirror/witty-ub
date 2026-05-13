#include "urma_0136_bondp_delete_jfc_resource_delete_failure_bondp_delete_comp_jfc.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0136BondpDeleteJfcResourceDeleteFailureBondpDeleteCompJfc> g_urma("urma_0136");

bool Urma0136BondpDeleteJfcResourceDeleteFailureBondpDeleteCompJfc::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete bdp_jfc"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0136BondpDeleteJfcResourceDeleteFailureBondpDeleteCompJfc::GetName() const
{
    return "bondp_delete_jfc 删除资源失败（bondp_delete_comp(jfc, BONDP_COMP_JFC) != URMA_SUCCESS）";
}

std::string Urma0136BondpDeleteJfcResourceDeleteFailureBondpDeleteCompJfc::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "ret";
}

RootCause Urma0136BondpDeleteJfcResourceDeleteFailureBondpDeleteCompJfc::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0136BondpDeleteJfcResourceDeleteFailureBondpDeleteCompJfc::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0136BondpDeleteJfcResourceDeleteFailureBondpDeleteCompJfc::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete bdp_jfc";
}

std::string Urma0136BondpDeleteJfcResourceDeleteFailureBondpDeleteCompJfc::GetId() const
{
    return "urma_0136";
}
} // namespace diag
