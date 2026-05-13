#include "urma_0165_bondp_import_jfr_invalid_param_ctx.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0165BondpImportJfrInvalidParamCtx> g_urma("urma_0165");

bool Urma0165BondpImportJfrInvalidParamCtx::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param ctx"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0165BondpImportJfrInvalidParamCtx::GetName() const
{
    return "bondp_import_jfr Invalid param ctx";
}

std::string Urma0165BondpImportJfrInvalidParamCtx::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_ctx(bdp_ctx)`；该路径返回 NULL";
}

RootCause Urma0165BondpImportJfrInvalidParamCtx::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0165BondpImportJfrInvalidParamCtx::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0165BondpImportJfrInvalidParamCtx::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param ctx";
}

std::string Urma0165BondpImportJfrInvalidParamCtx::GetId() const
{
    return "urma_0165";
}
} // namespace diag
