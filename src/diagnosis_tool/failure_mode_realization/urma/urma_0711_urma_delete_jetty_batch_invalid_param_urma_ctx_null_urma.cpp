#include "urma_0711_urma_delete_jetty_batch_invalid_param_urma_ctx_null_urma.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0711UrmaDeleteJettyBatchInvalidParamUrmaCtxNullUrma> g_urma("urma_0711");

bool Urma0711UrmaDeleteJettyBatchInvalidParamUrmaCtxNullUrma::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, index: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0711UrmaDeleteJettyBatchInvalidParamUrmaCtxNullUrma::GetName() const
{
    return "urma_delete_jetty_batch 参数非法（((urma_ctx) == NULL) || ((urma_ctx)->dev == NULL) || "
           "((urma_ctx)->dev->sysfs_dev == NULL) || (((ops)）";
}

std::string Urma0711UrmaDeleteJettyBatchInvalidParamUrmaCtxNullUrma::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `((urma_ctx) == NULL) || ((urma_ctx)->dev == NULL) || "
           "((urma_ctx)->dev->sysfs_dev == NULL) || (((ops)`";
}

RootCause Urma0711UrmaDeleteJettyBatchInvalidParamUrmaCtxNullUrma::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0711UrmaDeleteJettyBatchInvalidParamUrmaCtxNullUrma::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0711UrmaDeleteJettyBatchInvalidParamUrmaCtxNullUrma::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, index: %.";
}

std::string Urma0711UrmaDeleteJettyBatchInvalidParamUrmaCtxNullUrma::GetId() const
{
    return "urma_0711";
}
} // namespace diag
