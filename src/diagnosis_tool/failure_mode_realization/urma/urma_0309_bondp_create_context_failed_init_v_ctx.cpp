#include "urma_0309_bondp_create_context_failed_init_v_ctx.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0309BondpCreateContextFailedInitVCtx> g_urma("urma_0309");

bool Urma0309BondpCreateContextFailedInitVCtx::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to init v_ctx"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0309BondpCreateContextFailedInitVCtx::GetName() const
{
    return "bondp_create_context Failed to init v_ctx";
}

std::string Urma0309BondpCreateContextFailedInitVCtx::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret`";
}

RootCause Urma0309BondpCreateContextFailedInitVCtx::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0309BondpCreateContextFailedInitVCtx::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0309BondpCreateContextFailedInitVCtx::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to init v_ctx";
}

std::string Urma0309BondpCreateContextFailedInitVCtx::GetId() const
{
    return "urma_0309";
}
} // namespace diag
