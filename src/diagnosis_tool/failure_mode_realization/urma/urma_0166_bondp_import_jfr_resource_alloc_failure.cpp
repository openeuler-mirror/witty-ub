#include "urma_0166_bondp_import_jfr_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0166BondpImportJfrResourceAllocFailure> g_urma("urma_0166");

bool Urma0166BondpImportJfrResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc target jetty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0166BondpImportJfrResourceAllocFailure::GetName() const
{
    return "bondp_import_jfr 分配资源失败";
}

std::string Urma0166BondpImportJfrResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 NULL";
}

RootCause Urma0166BondpImportJfrResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0166BondpImportJfrResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0166BondpImportJfrResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc target jetty";
}

std::string Urma0166BondpImportJfrResourceAllocFailure::GetId() const
{
    return "urma_0166";
}
} // namespace diag
