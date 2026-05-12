#include "urma_1004_bondp_import_seg_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1004BondpImportSegResourceAllocFailure> g_urma("urma_1004");

bool Urma1004BondpImportSegResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc target seg"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1004BondpImportSegResourceAllocFailure::GetName() const
{
    return "bondp_import_seg 分配资源失败";
}

std::string Urma1004BondpImportSegResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 NULL";
}

RootCause Urma1004BondpImportSegResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1004BondpImportSegResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1004BondpImportSegResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc target seg";
}

std::string Urma1004BondpImportSegResourceAllocFailure::GetId() const
{
    return "urma_1004";
}
} // namespace diag
