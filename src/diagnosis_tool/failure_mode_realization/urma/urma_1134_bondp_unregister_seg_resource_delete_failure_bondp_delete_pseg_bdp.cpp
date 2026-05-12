#include "urma_1134_bondp_unregister_seg_resource_delete_failure_bondp_delete_pseg_bdp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1134BondpUnregisterSegResourceDeleteFailureBondpDeletePsegBdp> g_urma("urma_1134");

bool Urma1134BondpUnregisterSegResourceDeleteFailureBondpDeletePsegBdp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete pseg for vseg, token_id:%, handle:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1134BondpUnregisterSegResourceDeleteFailureBondpDeletePsegBdp::GetName() const
{
    return "bondp_unregister_seg 删除资源失败（bondp_delete_pseg(bdp_seg) != 0）";
}

std::string Urma1134BondpUnregisterSegResourceDeleteFailureBondpDeletePsegBdp::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "ret";
}

RootCause Urma1134BondpUnregisterSegResourceDeleteFailureBondpDeletePsegBdp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1134BondpUnregisterSegResourceDeleteFailureBondpDeletePsegBdp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1134BondpUnregisterSegResourceDeleteFailureBondpDeletePsegBdp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete pseg for vseg, token_id:%, handle:%.";
}

std::string Urma1134BondpUnregisterSegResourceDeleteFailureBondpDeletePsegBdp::GetId() const
{
    return "urma_1134";
}
} // namespace diag
