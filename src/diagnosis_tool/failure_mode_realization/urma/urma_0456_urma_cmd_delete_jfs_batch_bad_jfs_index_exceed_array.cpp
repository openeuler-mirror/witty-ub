#include "urma_0456_urma_cmd_delete_jfs_batch_bad_jfs_index_exceed_array.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0456UrmaCmdDeleteJfsBatchBadJfsIndexExceedArray> g_urma("urma_0456");

bool Urma0456UrmaCmdDeleteJfsBatchBadJfsIndexExceedArray::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"bad jfs index exceed array length, bad_jfs_index: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0456UrmaCmdDeleteJfsBatchBadJfsIndexExceedArray::GetName() const
{
    return "urma_cmd_delete_jfs_batch bad jfs index exceed array length, b";
}

std::string Urma0456UrmaCmdDeleteJfsBatchBadJfsIndexExceedArray::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `arg.out.bad_jfs_index >= jfs_num`；该路径返回 ret";
}

RootCause Urma0456UrmaCmdDeleteJfsBatchBadJfsIndexExceedArray::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0456UrmaCmdDeleteJfsBatchBadJfsIndexExceedArray::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0456UrmaCmdDeleteJfsBatchBadJfsIndexExceedArray::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：bad jfs index exceed array length, bad_jfs_index: %.";
}

std::string Urma0456UrmaCmdDeleteJfsBatchBadJfsIndexExceedArray::GetId() const
{
    return "urma_0456";
}
} // namespace diag
