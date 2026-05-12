#include "urma_0314_bondp_create_pseg_failed_register_pseg.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0314BondpCreatePsegFailedRegisterPseg> g_urma("urma_0314");

bool Urma0314BondpCreatePsegFailedRegisterPseg::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to register pseg %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0314BondpCreatePsegFailedRegisterPseg::GetName() const
{
    return "bondp_create_pseg Failed to register pseg %";
}

std::string Urma0314BondpCreatePsegFailedRegisterPseg::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0314BondpCreatePsegFailedRegisterPseg::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0314BondpCreatePsegFailedRegisterPseg::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0314BondpCreatePsegFailedRegisterPseg::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to register pseg %";
}

std::string Urma0314BondpCreatePsegFailedRegisterPseg::GetId() const
{
    return "urma_0314";
}
} // namespace diag
