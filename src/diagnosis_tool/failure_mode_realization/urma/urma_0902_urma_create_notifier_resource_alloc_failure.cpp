#include "urma_0902_urma_create_notifier_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0902UrmaCreateNotifierResourceAllocFailure> g_urma("urma_0902");

bool Urma0902UrmaCreateNotifierResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc notifier."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0902UrmaCreateNotifierResourceAllocFailure::GetName() const
{
    return "urma_create_notifier 分配资源失败";
}

std::string Urma0902UrmaCreateNotifierResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 NULL";
}

RootCause Urma0902UrmaCreateNotifierResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0902UrmaCreateNotifierResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0902UrmaCreateNotifierResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc notifier.";
}

std::string Urma0902UrmaCreateNotifierResourceAllocFailure::GetId() const
{
    return "urma_0902";
}
} // namespace diag
