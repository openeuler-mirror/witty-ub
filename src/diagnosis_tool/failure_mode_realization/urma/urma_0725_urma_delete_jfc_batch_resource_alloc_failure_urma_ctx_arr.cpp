#include "urma_0725_urma_delete_jfc_batch_resource_alloc_failure_urma_ctx_arr.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0725UrmaDeleteJfcBatchResourceAllocFailureUrmaCtxArr> g_urma("urma_0725");

bool Urma0725UrmaDeleteJfcBatchResourceAllocFailureUrmaCtxArr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to alloc memory."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0725UrmaDeleteJfcBatchResourceAllocFailureUrmaCtxArr::GetName() const
{
    return "urma_delete_jfc_batch 分配资源失败（urma_ctx_arr == NULL）";
}

std::string Urma0725UrmaDeleteJfcBatchResourceAllocFailureUrmaCtxArr::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 URMA_ENOMEM";
}

RootCause Urma0725UrmaDeleteJfcBatchResourceAllocFailureUrmaCtxArr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0725UrmaDeleteJfcBatchResourceAllocFailureUrmaCtxArr::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0725UrmaDeleteJfcBatchResourceAllocFailureUrmaCtxArr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to alloc memory.";
}

std::string Urma0725UrmaDeleteJfcBatchResourceAllocFailureUrmaCtxArr::GetId() const
{
    return "urma_0725";
}
} // namespace diag
