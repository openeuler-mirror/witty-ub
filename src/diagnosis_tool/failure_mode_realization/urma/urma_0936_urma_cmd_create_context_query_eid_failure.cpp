#include "urma_0936_urma_cmd_create_context_query_eid_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0936UrmaCmdCreateContextQueryEidFailure> g_urma("urma_0936");

bool Urma0936UrmaCmdCreateContextQueryEidFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to query eid."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0936UrmaCmdCreateContextQueryEidFailure::GetName() const
{
    return "urma_cmd_create_context 查询EID失败";
}

std::string Urma0936UrmaCmdCreateContextQueryEidFailure::GetRootCauseDesc() const
{
    return "设备或资源查询失败，可能由于设备不存在、名称不匹配、设备能力不可用或下游查询返回错误；该路径返回 -1";
}

RootCause Urma0936UrmaCmdCreateContextQueryEidFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0936UrmaCmdCreateContextQueryEidFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0936UrmaCmdCreateContextQueryEidFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to query eid.";
}

std::string Urma0936UrmaCmdCreateContextQueryEidFailure::GetId() const
{
    return "urma_0936";
}
} // namespace diag
