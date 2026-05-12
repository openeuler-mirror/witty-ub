#include "urma_0241_get_bjetty_ctx_cr_query_attr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0241GetBjettyCtxCrQueryAttrFailure> g_urma("urma_0241");

bool Urma0241GetBjettyCtxCrQueryAttrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to get comp, local_id: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0241GetBjettyCtxCrQueryAttrFailure::GetName() const
{
    return "get_bjetty_ctx_by_cr 查询属性失败";
}

std::string Urma0241GetBjettyCtxCrQueryAttrFailure::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 NULL";
}

RootCause Urma0241GetBjettyCtxCrQueryAttrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0241GetBjettyCtxCrQueryAttrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0241GetBjettyCtxCrQueryAttrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to get comp, local_id: %";
}

std::string Urma0241GetBjettyCtxCrQueryAttrFailure::GetId() const
{
    return "urma_0241";
}
} // namespace diag
