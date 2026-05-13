#include "urma_0453_urma_cmd_delete_jfs_batch_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0453UrmaCmdDeleteJfsBatchResourceDeleteFailure> g_urma("urma_0453");

bool Urma0453UrmaCmdDeleteJfsBatchResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfs not from the same dev, cannot delete in a batch, index: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0453UrmaCmdDeleteJfsBatchResourceDeleteFailure::GetName() const
{
    return "urma_cmd_delete_jfs_batch 删除资源失败";
}

std::string Urma0453UrmaCmdDeleteJfsBatchResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0453UrmaCmdDeleteJfsBatchResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0453UrmaCmdDeleteJfsBatchResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0453UrmaCmdDeleteJfsBatchResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfs not from the same dev, cannot delete in a batch, index: %.";
}

std::string Urma0453UrmaCmdDeleteJfsBatchResourceDeleteFailure::GetId() const
{
    return "urma_0453";
}
} // namespace diag
