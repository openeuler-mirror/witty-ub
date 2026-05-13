#include "urma_0208_bondp_create_comp_invalid_param_ctx.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0208BondpCreateCompInvalidParamCtx> g_urma("urma_0208");

bool Urma0208BondpCreateCompInvalidParamCtx::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param ctx"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0208BondpCreateCompInvalidParamCtx::GetName() const
{
    return "bondp_create_comp Invalid param ctx";
}

std::string Urma0208BondpCreateCompInvalidParamCtx::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_ctx(bdp_ctx)`；该路径返回 NULL";
}

RootCause Urma0208BondpCreateCompInvalidParamCtx::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0208BondpCreateCompInvalidParamCtx::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0208BondpCreateCompInvalidParamCtx::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param ctx";
}

std::string Urma0208BondpCreateCompInvalidParamCtx::GetId() const
{
    return "urma_0208";
}
} // namespace diag
