#include "urma_0727_urma_delete_jfc_batch_invalid_param_jfc_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0727UrmaDeleteJfcBatchInvalidParamJfcNull> g_urma("urma_0727");

bool Urma0727UrmaDeleteJfcBatchInvalidParamJfcNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, % jfc in the array is NULL."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0727UrmaDeleteJfcBatchInvalidParamJfcNull::GetName() const
{
    return "urma_delete_jfc_batch 参数非法（jfc == NULL）";
}

std::string Urma0727UrmaDeleteJfcBatchInvalidParamJfcNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL`";
}

RootCause Urma0727UrmaDeleteJfcBatchInvalidParamJfcNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0727UrmaDeleteJfcBatchInvalidParamJfcNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0727UrmaDeleteJfcBatchInvalidParamJfcNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, % jfc in the array is NULL.";
}

std::string Urma0727UrmaDeleteJfcBatchInvalidParamJfcNull::GetId() const
{
    return "urma_0727";
}
} // namespace diag
