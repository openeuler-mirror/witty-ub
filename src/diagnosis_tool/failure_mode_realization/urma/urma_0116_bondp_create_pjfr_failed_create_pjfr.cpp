#include "urma_0116_bondp_create_pjfr_failed_create_pjfr.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0116BondpCreatePjfrFailedCreatePjfr> g_urma("urma_0116");

bool Urma0116BondpCreatePjfrFailedCreatePjfr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create pjfr %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0116BondpCreatePjfrFailedCreatePjfr::GetName() const
{
    return "bondp_create_pjfr Failed to create pjfr %.";
}

std::string Urma0116BondpCreatePjfrFailedCreatePjfr::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0116BondpCreatePjfrFailedCreatePjfr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0116BondpCreatePjfrFailedCreatePjfr::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0116BondpCreatePjfrFailedCreatePjfr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create pjfr %.";
}

std::string Urma0116BondpCreatePjfrFailedCreatePjfr::GetId() const
{
    return "urma_0116";
}
} // namespace diag
