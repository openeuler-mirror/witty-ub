#include "urma_0327_deepcopy_jfs_wr_node_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0327DeepcopyJfsWrNodeResourceAllocFailure> g_urma("urma_0327");

bool Urma0327DeepcopyJfsWrNodeResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Malloc wr failed"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0327DeepcopyJfsWrNodeResourceAllocFailure::GetName() const
{
    return "deepcopy_jfs_wr_node 分配资源失败";
}

std::string Urma0327DeepcopyJfsWrNodeResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 NULL";
}

RootCause Urma0327DeepcopyJfsWrNodeResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0327DeepcopyJfsWrNodeResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0327DeepcopyJfsWrNodeResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Malloc wr failed";
}

std::string Urma0327DeepcopyJfsWrNodeResourceAllocFailure::GetId() const
{
    return "urma_0327";
}
} // namespace diag
