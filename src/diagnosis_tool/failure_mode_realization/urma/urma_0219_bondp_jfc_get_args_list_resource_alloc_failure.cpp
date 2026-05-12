#include "urma_0219_bondp_jfc_get_args_list_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0219BondpJfcGetArgsListResourceAllocFailure> g_urma("urma_0219");

bool Urma0219BondpJfcGetArgsListResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc args"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0219BondpJfcGetArgsListResourceAllocFailure::GetName() const
{
    return "bondp_jfc_get_args_list 分配资源失败";
}

std::string Urma0219BondpJfcGetArgsListResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 NULL";
}

RootCause Urma0219BondpJfcGetArgsListResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0219BondpJfcGetArgsListResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0219BondpJfcGetArgsListResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc args";
}

std::string Urma0219BondpJfcGetArgsListResourceAllocFailure::GetId() const
{
    return "urma_0219";
}
} // namespace diag
