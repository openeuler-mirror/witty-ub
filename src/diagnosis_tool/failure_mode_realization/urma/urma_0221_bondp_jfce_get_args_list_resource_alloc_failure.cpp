#include "urma_0221_bondp_jfce_get_args_list_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0221BondpJfceGetArgsListResourceAllocFailure> g_urma("urma_0221");

bool Urma0221BondpJfceGetArgsListResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc jfce args"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0221BondpJfceGetArgsListResourceAllocFailure::GetName() const
{
    return "bondp_jfce_get_args_list 分配资源失败";
}

std::string Urma0221BondpJfceGetArgsListResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 NULL";
}

RootCause Urma0221BondpJfceGetArgsListResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0221BondpJfceGetArgsListResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0221BondpJfceGetArgsListResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc jfce args";
}

std::string Urma0221BondpJfceGetArgsListResourceAllocFailure::GetId() const
{
    return "urma_0221";
}
} // namespace diag
