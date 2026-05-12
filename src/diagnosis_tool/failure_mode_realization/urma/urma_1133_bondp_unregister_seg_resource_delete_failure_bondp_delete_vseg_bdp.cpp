#include "urma_1133_bondp_unregister_seg_resource_delete_failure_bondp_delete_vseg_bdp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1133BondpUnregisterSegResourceDeleteFailureBondpDeleteVsegBdp> g_urma("urma_1133");

bool Urma1133BondpUnregisterSegResourceDeleteFailureBondpDeleteVsegBdp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete vseg, token_id:%, handle:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1133BondpUnregisterSegResourceDeleteFailureBondpDeleteVsegBdp::GetName() const
{
    return "bondp_unregister_seg 删除资源失败（bondp_delete_vseg(bdp_seg) != 0）";
}

std::string Urma1133BondpUnregisterSegResourceDeleteFailureBondpDeleteVsegBdp::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma1133BondpUnregisterSegResourceDeleteFailureBondpDeleteVsegBdp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1133BondpUnregisterSegResourceDeleteFailureBondpDeleteVsegBdp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1133BondpUnregisterSegResourceDeleteFailureBondpDeleteVsegBdp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete vseg, token_id:%, handle:%.";
}

std::string Urma1133BondpUnregisterSegResourceDeleteFailureBondpDeleteVsegBdp::GetId() const
{
    return "urma_1133";
}
} // namespace diag
