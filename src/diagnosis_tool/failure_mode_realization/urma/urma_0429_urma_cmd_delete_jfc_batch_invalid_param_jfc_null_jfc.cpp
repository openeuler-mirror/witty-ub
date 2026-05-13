#include "urma_0429_urma_cmd_delete_jfc_batch_invalid_param_jfc_null_jfc.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0429UrmaCmdDeleteJfcBatchInvalidParamJfcNullJfc> g_urma("urma_0429");

bool Urma0429UrmaCmdDeleteJfcBatchInvalidParamJfcNullJfc::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, index: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0429UrmaCmdDeleteJfcBatchInvalidParamJfcNullJfc::GetName() const
{
    return "urma_cmd_delete_jfc_batch 参数非法（jfc == NULL || jfc->urma_ctx == NULL）";
}

std::string Urma0429UrmaCmdDeleteJfcBatchInvalidParamJfcNullJfc::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL || jfc->urma_ctx == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0429UrmaCmdDeleteJfcBatchInvalidParamJfcNullJfc::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0429UrmaCmdDeleteJfcBatchInvalidParamJfcNullJfc::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0429UrmaCmdDeleteJfcBatchInvalidParamJfcNullJfc::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, index: %.";
}

std::string Urma0429UrmaCmdDeleteJfcBatchInvalidParamJfcNullJfc::GetId() const
{
    return "urma_0429";
}
} // namespace diag
