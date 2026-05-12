#include "urma_0200_import_pjetty_primary_eid_primary_dev_has_null_ctx.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0200ImportPjettyPrimaryEidPrimaryDevHasNullCtx> g_urma("urma_0200");

bool Urma0200ImportPjettyPrimaryEidPrimaryDevHasNullCtx::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Primary dev has NULL ctx"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0200ImportPjettyPrimaryEidPrimaryDevHasNullCtx::GetName() const
{
    return "import_pjetty_for_primary_eid Primary dev has NULL ctx";
}

std::string Urma0200ImportPjettyPrimaryEidPrimaryDevHasNullCtx::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bdp_ctx->p_ctxs[i] == NULL`；该路径返回 -1";
}

RootCause Urma0200ImportPjettyPrimaryEidPrimaryDevHasNullCtx::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0200ImportPjettyPrimaryEidPrimaryDevHasNullCtx::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0200ImportPjettyPrimaryEidPrimaryDevHasNullCtx::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Primary dev has NULL ctx";
}

std::string Urma0200ImportPjettyPrimaryEidPrimaryDevHasNullCtx::GetId() const
{
    return "urma_0200";
}
} // namespace diag
