#include "urma_0922_get_dev_ctx_name_query_attr_failure_eid_index_0.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0922GetDevCtxNameQueryAttrFailureEidIndex0> g_urma("urma_0922");

bool Urma0922GetDevCtxNameQueryAttrFailureEidIndex0::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to get eid_idx"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0922GetDevCtxNameQueryAttrFailureEidIndex0::GetName() const
{
    return "get_dev_and_ctx_by_name 查询属性失败（eid_index < 0）";
}

std::string Urma0922GetDevCtxNameQueryAttrFailureEidIndex0::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `eid_index < 0`；该路径返回 -1";
}

RootCause Urma0922GetDevCtxNameQueryAttrFailureEidIndex0::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0922GetDevCtxNameQueryAttrFailureEidIndex0::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0922GetDevCtxNameQueryAttrFailureEidIndex0::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to get eid_idx";
}

std::string Urma0922GetDevCtxNameQueryAttrFailureEidIndex0::GetId() const
{
    return "urma_0922";
}
} // namespace diag
