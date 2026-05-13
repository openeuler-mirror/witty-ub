#include "urma_0104_bondp_create_jfr_create_jfr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0104BondpCreateJfrCreateJfrFailure> g_urma("urma_0104");

bool Urma0104BondpCreateJfrCreateJfrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create jfr datapath ctx"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0104BondpCreateJfrCreateJfrFailure::GetName() const
{
    return "bondp_create_jfr 创建JFR失败";
}

std::string Urma0104BondpCreateJfrCreateJfrFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0104BondpCreateJfrCreateJfrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0104BondpCreateJfrCreateJfrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0104BondpCreateJfrCreateJfrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create jfr datapath ctx";
}

std::string Urma0104BondpCreateJfrCreateJfrFailure::GetId() const
{
    return "urma_0104";
}
} // namespace diag
