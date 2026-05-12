#include "urma_0708_urma_delete_jetty_batch_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0708UrmaDeleteJettyBatchResourceAllocFailure> g_urma("urma_0708");

bool Urma0708UrmaDeleteJettyBatchResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc memory."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0708UrmaDeleteJettyBatchResourceAllocFailure::GetName() const
{
    return "urma_delete_jetty_batch 分配资源失败";
}

std::string Urma0708UrmaDeleteJettyBatchResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 URMA_ENOMEM";
}

RootCause Urma0708UrmaDeleteJettyBatchResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0708UrmaDeleteJettyBatchResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0708UrmaDeleteJettyBatchResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc memory.";
}

std::string Urma0708UrmaDeleteJettyBatchResourceAllocFailure::GetId() const
{
    return "urma_0708";
}
} // namespace diag
