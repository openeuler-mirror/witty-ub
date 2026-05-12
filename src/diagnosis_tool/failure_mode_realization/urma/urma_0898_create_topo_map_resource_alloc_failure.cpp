#include "urma_0898_create_topo_map_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0898CreateTopoMapResourceAllocFailure> g_urma("urma_0898");

bool Urma0898CreateTopoMapResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc topo_map"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0898CreateTopoMapResourceAllocFailure::GetName() const
{
    return "create_topo_map 分配资源失败";
}

std::string Urma0898CreateTopoMapResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 NULL";
}

RootCause Urma0898CreateTopoMapResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0898CreateTopoMapResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0898CreateTopoMapResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc topo_map";
}

std::string Urma0898CreateTopoMapResourceAllocFailure::GetId() const
{
    return "urma_0898";
}
} // namespace diag
