#include "urma_0018_bondp_global_ctx_init_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0018BondpGlobalCtxInitResourceAllocFailure> g_urma("urma_0018");

bool Urma0018BondpGlobalCtxInitResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc global context"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0018BondpGlobalCtxInitResourceAllocFailure::GetName() const
{
    return "bondp_global_ctx_init 分配资源失败";
}

std::string Urma0018BondpGlobalCtxInitResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 -1";
}

RootCause Urma0018BondpGlobalCtxInitResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0018BondpGlobalCtxInitResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0018BondpGlobalCtxInitResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc global context";
}

std::string Urma0018BondpGlobalCtxInitResourceAllocFailure::GetId() const
{
    return "urma_0018";
}
} // namespace diag
