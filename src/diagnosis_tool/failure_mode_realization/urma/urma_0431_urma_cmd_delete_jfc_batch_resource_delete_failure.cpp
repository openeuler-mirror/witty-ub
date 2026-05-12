#include "urma_0431_urma_cmd_delete_jfc_batch_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0431UrmaCmdDeleteJfcBatchResourceDeleteFailure> g_urma("urma_0431");

bool Urma0431UrmaCmdDeleteJfcBatchResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfc not from the same dev, cannot delete in a batch, index: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0431UrmaCmdDeleteJfcBatchResourceDeleteFailure::GetName() const
{
    return "urma_cmd_delete_jfc_batch 删除资源失败";
}

std::string Urma0431UrmaCmdDeleteJfcBatchResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0431UrmaCmdDeleteJfcBatchResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0431UrmaCmdDeleteJfcBatchResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0431UrmaCmdDeleteJfcBatchResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfc not from the same dev, cannot delete in a batch, index: %.";
}

std::string Urma0431UrmaCmdDeleteJfcBatchResourceDeleteFailure::GetId() const
{
    return "urma_0431";
}
} // namespace diag
