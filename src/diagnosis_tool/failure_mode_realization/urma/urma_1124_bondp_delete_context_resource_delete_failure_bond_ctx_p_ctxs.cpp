#include "urma_1124_bondp_delete_context_resource_delete_failure_bond_ctx_p_ctxs.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1124BondpDeleteContextResourceDeleteFailureBondCtxPCtxs> g_urma("urma_1124");

bool Urma1124BondpDeleteContextResourceDeleteFailureBondCtxPCtxs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete context %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1124BondpDeleteContextResourceDeleteFailureBondCtxPCtxs::GetName() const
{
    return "bondp_delete_context 删除资源失败（bond_ctx->p_ctxs[i] && urma_delete_context(bond_ctx->p_ctxs[i])）";
}

std::string Urma1124BondpDeleteContextResourceDeleteFailureBondCtxPCtxs::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma1124BondpDeleteContextResourceDeleteFailureBondCtxPCtxs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1124BondpDeleteContextResourceDeleteFailureBondCtxPCtxs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1124BondpDeleteContextResourceDeleteFailureBondCtxPCtxs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete context %";
}

std::string Urma1124BondpDeleteContextResourceDeleteFailureBondCtxPCtxs::GetId() const
{
    return "urma_1124";
}
} // namespace diag
