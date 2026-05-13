#include "urma_0242_get_bjetty_ctx_cr_null_bjetty_ctx_bdp_comp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0242GetBjettyCtxCrNullBjettyCtxBdpComp> g_urma("urma_0242");

bool Urma0242GetBjettyCtxCrNullBjettyCtxBdpComp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Null bjetty_ctx in bdp_comp"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0242GetBjettyCtxCrNullBjettyCtxBdpComp::GetName() const
{
    return "get_bjetty_ctx_by_cr Null bjetty_ctx in bdp_comp";
}

std::string Urma0242GetBjettyCtxCrNullBjettyCtxBdpComp::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 NULL";
}

RootCause Urma0242GetBjettyCtxCrNullBjettyCtxBdpComp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0242GetBjettyCtxCrNullBjettyCtxBdpComp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0242GetBjettyCtxCrNullBjettyCtxBdpComp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Null bjetty_ctx in bdp_comp";
}

std::string Urma0242GetBjettyCtxCrNullBjettyCtxBdpComp::GetId() const
{
    return "urma_0242";
}
} // namespace diag
