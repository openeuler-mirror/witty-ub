#include "urma_0982_urma_create_context_query_eid_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0982UrmaCreateContextQueryEidFailure> g_urma("urma_0982");

bool Urma0982UrmaCreateContextQueryEidFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to query eid."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0982UrmaCreateContextQueryEidFailure::GetName() const
{
    return "urma_create_context 查询EID失败";
}

std::string Urma0982UrmaCreateContextQueryEidFailure::GetRootCauseDesc() const
{
    return "设备或资源查询失败，可能由于设备不存在、名称不匹配、设备能力不可用或下游查询返回错误；该路径返回 NULL";
}

RootCause Urma0982UrmaCreateContextQueryEidFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0982UrmaCreateContextQueryEidFailure::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string Urma0982UrmaCreateContextQueryEidFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to query eid.";
}

std::string Urma0982UrmaCreateContextQueryEidFailure::GetId() const
{
    return "urma_0982";
}
} // namespace diag
