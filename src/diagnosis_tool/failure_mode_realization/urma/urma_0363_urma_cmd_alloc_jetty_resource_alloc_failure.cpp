#include "urma_0363_urma_cmd_alloc_jetty_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0363UrmaCmdAllocJettyResourceAllocFailure> g_urma("urma_0363");

bool Urma0363UrmaCmdAllocJettyResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"failed to init alloc jetty cmd"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0363UrmaCmdAllocJettyResourceAllocFailure::GetName() const
{
    return "urma_cmd_alloc_jetty 分配资源失败";
}

std::string Urma0363UrmaCmdAllocJettyResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 -1";
}

RootCause Urma0363UrmaCmdAllocJettyResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0363UrmaCmdAllocJettyResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0363UrmaCmdAllocJettyResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：failed to init alloc jetty cmd";
}

std::string Urma0363UrmaCmdAllocJettyResourceAllocFailure::GetId() const
{
    return "urma_0363";
}
} // namespace diag
