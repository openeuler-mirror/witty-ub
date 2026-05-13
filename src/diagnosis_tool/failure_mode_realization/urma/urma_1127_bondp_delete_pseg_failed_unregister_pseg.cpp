#include "urma_1127_bondp_delete_pseg_failed_unregister_pseg.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1127BondpDeletePsegFailedUnregisterPseg> g_urma("urma_1127");

bool Urma1127BondpDeletePsegFailedUnregisterPseg::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to unregister pseg %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1127BondpDeletePsegFailedUnregisterPseg::GetName() const
{
    return "bondp_delete_pseg Failed to unregister pseg %";
}

std::string Urma1127BondpDeletePsegFailedUnregisterPseg::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "ret";
}

RootCause Urma1127BondpDeletePsegFailedUnregisterPseg::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1127BondpDeletePsegFailedUnregisterPseg::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1127BondpDeletePsegFailedUnregisterPseg::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to unregister pseg %";
}

std::string Urma1127BondpDeletePsegFailedUnregisterPseg::GetId() const
{
    return "urma_1127";
}
} // namespace diag
