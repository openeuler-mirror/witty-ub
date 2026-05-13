#include "urma_0440_urma_cmd_delete_jfr_batch_invalid_param_jfr_null_jfr.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0440UrmaCmdDeleteJfrBatchInvalidParamJfrNullJfr> g_urma("urma_0440");

bool Urma0440UrmaCmdDeleteJfrBatchInvalidParamJfrNullJfr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, index: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0440UrmaCmdDeleteJfrBatchInvalidParamJfrNullJfr::GetName() const
{
    return "urma_cmd_delete_jfr_batch 参数非法（jfr == NULL || jfr->urma_ctx == NULL）";
}

std::string Urma0440UrmaCmdDeleteJfrBatchInvalidParamJfrNullJfr::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL || jfr->urma_ctx == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0440UrmaCmdDeleteJfrBatchInvalidParamJfrNullJfr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0440UrmaCmdDeleteJfrBatchInvalidParamJfrNullJfr::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0440UrmaCmdDeleteJfrBatchInvalidParamJfrNullJfr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, index: %.";
}

std::string Urma0440UrmaCmdDeleteJfrBatchInvalidParamJfrNullJfr::GetId() const
{
    return "urma_0440";
}
} // namespace diag
