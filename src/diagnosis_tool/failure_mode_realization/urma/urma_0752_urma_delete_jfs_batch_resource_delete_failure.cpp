#include "urma_0752_urma_delete_jfs_batch_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0752UrmaDeleteJfsBatchResourceDeleteFailure> g_urma("urma_0752");

bool Urma0752UrmaDeleteJfsBatchResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete jfs batch."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0752UrmaDeleteJfsBatchResourceDeleteFailure::GetName() const
{
    return "urma_delete_jfs_batch 删除资源失败";
}

std::string Urma0752UrmaDeleteJfsBatchResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0752UrmaDeleteJfsBatchResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0752UrmaDeleteJfsBatchResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0752UrmaDeleteJfsBatchResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete jfs batch.";
}

std::string Urma0752UrmaDeleteJfsBatchResourceDeleteFailure::GetId() const
{
    return "urma_0752";
}
} // namespace diag
