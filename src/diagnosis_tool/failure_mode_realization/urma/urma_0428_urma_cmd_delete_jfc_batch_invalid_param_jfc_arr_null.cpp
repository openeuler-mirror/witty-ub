#include "urma_0428_urma_cmd_delete_jfc_batch_invalid_param_jfc_arr_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0428UrmaCmdDeleteJfcBatchInvalidParamJfcArrNull> g_urma("urma_0428");

bool Urma0428UrmaCmdDeleteJfcBatchInvalidParamJfcArrNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0428UrmaCmdDeleteJfcBatchInvalidParamJfcArrNull::GetName() const
{
    return "urma_cmd_delete_jfc_batch 参数非法（jfc_arr == NULL || jfc_num <= 0 || bad_jfc == NULL）";
}

std::string Urma0428UrmaCmdDeleteJfcBatchInvalidParamJfcArrNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc_arr == NULL || jfc_num <= 0 || bad_jfc == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0428UrmaCmdDeleteJfcBatchInvalidParamJfcArrNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0428UrmaCmdDeleteJfcBatchInvalidParamJfcArrNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0428UrmaCmdDeleteJfcBatchInvalidParamJfcArrNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0428UrmaCmdDeleteJfcBatchInvalidParamJfcArrNull::GetId() const
{
    return "urma_0428";
}
} // namespace diag
