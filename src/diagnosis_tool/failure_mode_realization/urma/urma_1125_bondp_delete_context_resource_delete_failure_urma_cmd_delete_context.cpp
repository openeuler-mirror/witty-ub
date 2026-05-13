#include "urma_1125_bondp_delete_context_resource_delete_failure_urma_cmd_delete_context.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1125BondpDeleteContextResourceDeleteFailureUrmaCmdDeleteContext> g_urma("urma_1125");

bool Urma1125BondpDeleteContextResourceDeleteFailureUrmaCmdDeleteContext::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to urma_cmd_delete_context"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1125BondpDeleteContextResourceDeleteFailureUrmaCmdDeleteContext::GetName() const
{
    return "bondp_delete_context 删除资源失败（urma_cmd_delete_context(&bond_ctx->v_ctx)）";
}

std::string Urma1125BondpDeleteContextResourceDeleteFailureUrmaCmdDeleteContext::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma1125BondpDeleteContextResourceDeleteFailureUrmaCmdDeleteContext::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1125BondpDeleteContextResourceDeleteFailureUrmaCmdDeleteContext::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1125BondpDeleteContextResourceDeleteFailureUrmaCmdDeleteContext::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to urma_cmd_delete_context";
}

std::string Urma1125BondpDeleteContextResourceDeleteFailureUrmaCmdDeleteContext::GetId() const
{
    return "urma_1125";
}
} // namespace diag
