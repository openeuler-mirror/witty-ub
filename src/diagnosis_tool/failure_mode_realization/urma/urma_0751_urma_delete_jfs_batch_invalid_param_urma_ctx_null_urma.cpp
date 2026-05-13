#include "urma_0751_urma_delete_jfs_batch_invalid_param_urma_ctx_null_urma.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0751UrmaDeleteJfsBatchInvalidParamUrmaCtxNullUrma> g_urma("urma_0751");

bool Urma0751UrmaDeleteJfsBatchInvalidParamUrmaCtxNullUrma::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, index: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0751UrmaDeleteJfsBatchInvalidParamUrmaCtxNullUrma::GetName() const
{
    return "urma_delete_jfs_batch 参数非法（((urma_ctx) == NULL) || ((urma_ctx)->dev == NULL) || "
           "((urma_ctx)->dev->sysfs_dev == NULL) || (((ops)）";
}

std::string Urma0751UrmaDeleteJfsBatchInvalidParamUrmaCtxNullUrma::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `((urma_ctx) == NULL) || ((urma_ctx)->dev == NULL) || "
           "((urma_ctx)->dev->sysfs_dev == NULL) || (((ops)`";
}

RootCause Urma0751UrmaDeleteJfsBatchInvalidParamUrmaCtxNullUrma::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0751UrmaDeleteJfsBatchInvalidParamUrmaCtxNullUrma::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0751UrmaDeleteJfsBatchInvalidParamUrmaCtxNullUrma::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, index: %.";
}

std::string Urma0751UrmaDeleteJfsBatchInvalidParamUrmaCtxNullUrma::GetId() const
{
    return "urma_0751";
}
} // namespace diag
