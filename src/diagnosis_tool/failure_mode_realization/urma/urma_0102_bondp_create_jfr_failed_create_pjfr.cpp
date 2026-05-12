#include "urma_0102_bondp_create_jfr_failed_create_pjfr.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0102BondpCreateJfrFailedCreatePjfr> g_urma("urma_0102");

bool Urma0102BondpCreateJfrFailedCreatePjfr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create pjfr"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0102BondpCreateJfrFailedCreatePjfr::GetName() const
{
    return "bondp_create_jfr Failed to create pjfr";
}

std::string Urma0102BondpCreateJfrFailedCreatePjfr::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0102BondpCreateJfrFailedCreatePjfr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0102BondpCreateJfrFailedCreatePjfr::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0102BondpCreateJfrFailedCreatePjfr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create pjfr";
}

std::string Urma0102BondpCreateJfrFailedCreatePjfr::GetId() const
{
    return "urma_0102";
}
} // namespace diag
