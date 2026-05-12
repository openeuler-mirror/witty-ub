#include "urma_0310_bondp_create_context_create_context_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0310BondpCreateContextCreateContextFailure> g_urma("urma_0310");

bool Urma0310BondpCreateContextCreateContextFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create context"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0310BondpCreateContextCreateContextFailure::GetName() const
{
    return "bondp_create_context 创建context失败";
}

std::string Urma0310BondpCreateContextCreateContextFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0310BondpCreateContextCreateContextFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0310BondpCreateContextCreateContextFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0310BondpCreateContextCreateContextFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create context";
}

std::string Urma0310BondpCreateContextCreateContextFailure::GetId() const
{
    return "urma_0310";
}
} // namespace diag
