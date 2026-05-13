#include "urma_0728_urma_delete_jfc_batch_invalid_param_urma_ctx_null_urma.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0728UrmaDeleteJfcBatchInvalidParamUrmaCtxNullUrma> g_urma("urma_0728");

bool Urma0728UrmaDeleteJfcBatchInvalidParamUrmaCtxNullUrma::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, index: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0728UrmaDeleteJfcBatchInvalidParamUrmaCtxNullUrma::GetName() const
{
    return "urma_delete_jfc_batch 参数非法（((urma_ctx) == NULL) || ((urma_ctx)->dev == NULL) || "
           "((urma_ctx)->dev->sysfs_dev == NULL) || (((ops)）";
}

std::string Urma0728UrmaDeleteJfcBatchInvalidParamUrmaCtxNullUrma::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `((urma_ctx) == NULL) || ((urma_ctx)->dev == NULL) || "
           "((urma_ctx)->dev->sysfs_dev == NULL) || (((ops)`";
}

RootCause Urma0728UrmaDeleteJfcBatchInvalidParamUrmaCtxNullUrma::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0728UrmaDeleteJfcBatchInvalidParamUrmaCtxNullUrma::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0728UrmaDeleteJfcBatchInvalidParamUrmaCtxNullUrma::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, index: %.";
}

std::string Urma0728UrmaDeleteJfcBatchInvalidParamUrmaCtxNullUrma::GetId() const
{
    return "urma_0728";
}
} // namespace diag
