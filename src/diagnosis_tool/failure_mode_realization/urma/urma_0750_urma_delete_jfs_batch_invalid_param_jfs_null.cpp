#include "urma_0750_urma_delete_jfs_batch_invalid_param_jfs_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0750UrmaDeleteJfsBatchInvalidParamJfsNull> g_urma("urma_0750");

bool Urma0750UrmaDeleteJfsBatchInvalidParamJfsNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, index: % jfs in the array is NULL."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0750UrmaDeleteJfsBatchInvalidParamJfsNull::GetName() const
{
    return "urma_delete_jfs_batch 参数非法（jfs == NULL）";
}

std::string Urma0750UrmaDeleteJfsBatchInvalidParamJfsNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL`";
}

RootCause Urma0750UrmaDeleteJfsBatchInvalidParamJfsNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0750UrmaDeleteJfsBatchInvalidParamJfsNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0750UrmaDeleteJfsBatchInvalidParamJfsNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, index: % jfs in the array is NULL.";
}

std::string Urma0750UrmaDeleteJfsBatchInvalidParamJfsNull::GetId() const
{
    return "urma_0750";
}
} // namespace diag
