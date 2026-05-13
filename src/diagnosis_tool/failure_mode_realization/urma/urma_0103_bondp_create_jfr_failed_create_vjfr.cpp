#include "urma_0103_bondp_create_jfr_failed_create_vjfr.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0103BondpCreateJfrFailedCreateVjfr> g_urma("urma_0103");

bool Urma0103BondpCreateJfrFailedCreateVjfr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create vjfr"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0103BondpCreateJfrFailedCreateVjfr::GetName() const
{
    return "bondp_create_jfr Failed to create vjfr";
}

std::string Urma0103BondpCreateJfrFailedCreateVjfr::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0103BondpCreateJfrFailedCreateVjfr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0103BondpCreateJfrFailedCreateVjfr::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0103BondpCreateJfrFailedCreateVjfr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create vjfr";
}

std::string Urma0103BondpCreateJfrFailedCreateVjfr::GetId() const
{
    return "urma_0103";
}
} // namespace diag
