#include "urma_0617_urma_alloc_jetty_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0617UrmaAllocJettyResourceAllocFailure> g_urma("urma_0617");

bool Urma0617UrmaAllocJettyResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"alloc_jetty failed."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0617UrmaAllocJettyResourceAllocFailure::GetName() const
{
    return "urma_alloc_jetty 分配资源失败";
}

std::string Urma0617UrmaAllocJettyResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 status";
}

RootCause Urma0617UrmaAllocJettyResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0617UrmaAllocJettyResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0617UrmaAllocJettyResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：alloc_jetty failed.";
}

std::string Urma0617UrmaAllocJettyResourceAllocFailure::GetId() const
{
    return "urma_0617";
}
} // namespace diag
