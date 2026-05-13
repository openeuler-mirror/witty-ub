#include "urma_0308_bondp_create_context_failed_create_ctx.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0308BondpCreateContextFailedCreateCtx> g_urma("urma_0308");

bool Urma0308BondpCreateContextFailedCreateCtx::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create ctx"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0308BondpCreateContextFailedCreateCtx::GetName() const
{
    return "bondp_create_context Failed to create ctx";
}

std::string Urma0308BondpCreateContextFailedCreateCtx::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma0308BondpCreateContextFailedCreateCtx::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0308BondpCreateContextFailedCreateCtx::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0308BondpCreateContextFailedCreateCtx::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create ctx";
}

std::string Urma0308BondpCreateContextFailedCreateCtx::GetId() const
{
    return "urma_0308";
}
} // namespace diag
