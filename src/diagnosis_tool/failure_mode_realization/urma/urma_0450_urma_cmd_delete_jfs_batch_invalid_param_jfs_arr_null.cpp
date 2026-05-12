#include "urma_0450_urma_cmd_delete_jfs_batch_invalid_param_jfs_arr_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0450UrmaCmdDeleteJfsBatchInvalidParamJfsArrNull> g_urma("urma_0450");

bool Urma0450UrmaCmdDeleteJfsBatchInvalidParamJfsArrNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0450UrmaCmdDeleteJfsBatchInvalidParamJfsArrNull::GetName() const
{
    return "urma_cmd_delete_jfs_batch 参数非法（jfs_arr == NULL || jfs_num <= 0 || bad_jfs == NULL）";
}

std::string Urma0450UrmaCmdDeleteJfsBatchInvalidParamJfsArrNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs_arr == NULL || jfs_num <= 0 || bad_jfs == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0450UrmaCmdDeleteJfsBatchInvalidParamJfsArrNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0450UrmaCmdDeleteJfsBatchInvalidParamJfsArrNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0450UrmaCmdDeleteJfsBatchInvalidParamJfsArrNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0450UrmaCmdDeleteJfsBatchInvalidParamJfsArrNull::GetId() const
{
    return "urma_0450";
}
} // namespace diag
