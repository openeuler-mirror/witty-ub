#include "urma_0321_deepcopy_jfr_wr_node_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0321DeepcopyJfrWrNodeResourceAllocFailure> g_urma("urma_0321");

bool Urma0321DeepcopyJfrWrNodeResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Malloc wr failed"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0321DeepcopyJfrWrNodeResourceAllocFailure::GetName() const
{
    return "deepcopy_jfr_wr_node 分配资源失败";
}

std::string Urma0321DeepcopyJfrWrNodeResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 NULL";
}

RootCause Urma0321DeepcopyJfrWrNodeResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0321DeepcopyJfrWrNodeResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0321DeepcopyJfrWrNodeResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Malloc wr failed";
}

std::string Urma0321DeepcopyJfrWrNodeResourceAllocFailure::GetId() const
{
    return "urma_0321";
}
} // namespace diag
