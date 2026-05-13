#include "urma_1085_deepcopy_sg_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1085DeepcopySgResourceAllocFailure> g_urma("urma_1085");

bool Urma1085DeepcopySgResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc dst sge"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1085DeepcopySgResourceAllocFailure::GetName() const
{
    return "deepcopy_sg 分配资源失败";
}

std::string Urma1085DeepcopySgResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 -1";
}

RootCause Urma1085DeepcopySgResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1085DeepcopySgResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1085DeepcopySgResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc dst sge";
}

std::string Urma1085DeepcopySgResourceAllocFailure::GetId() const
{
    return "urma_1085";
}
} // namespace diag
