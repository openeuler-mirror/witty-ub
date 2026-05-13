#include "urma_0156_bondp_import_jetty_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0156BondpImportJettyResourceAllocFailure> g_urma("urma_0156");

bool Urma0156BondpImportJettyResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc target jetty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0156BondpImportJettyResourceAllocFailure::GetName() const
{
    return "bondp_import_jetty 分配资源失败";
}

std::string Urma0156BondpImportJettyResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 NULL";
}

RootCause Urma0156BondpImportJettyResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0156BondpImportJettyResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0156BondpImportJettyResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc target jetty";
}

std::string Urma0156BondpImportJettyResourceAllocFailure::GetId() const
{
    return "urma_0156";
}
} // namespace diag
