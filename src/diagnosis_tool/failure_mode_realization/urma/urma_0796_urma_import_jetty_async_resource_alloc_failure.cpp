#include "urma_0796_urma_import_jetty_async_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0796UrmaImportJettyAsyncResourceAllocFailure> g_urma("urma_0796");

bool Urma0796UrmaImportJettyAsyncResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc incomplete_tjetty."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0796UrmaImportJettyAsyncResourceAllocFailure::GetName() const
{
    return "urma_import_jetty_async 分配资源失败";
}

std::string Urma0796UrmaImportJettyAsyncResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 NULL";
}

RootCause Urma0796UrmaImportJettyAsyncResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0796UrmaImportJettyAsyncResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0796UrmaImportJettyAsyncResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc incomplete_tjetty.";
}

std::string Urma0796UrmaImportJettyAsyncResourceAllocFailure::GetId() const
{
    return "urma_0796";
}
} // namespace diag
