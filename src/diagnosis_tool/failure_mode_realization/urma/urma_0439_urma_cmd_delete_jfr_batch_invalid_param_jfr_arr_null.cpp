#include "urma_0439_urma_cmd_delete_jfr_batch_invalid_param_jfr_arr_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0439UrmaCmdDeleteJfrBatchInvalidParamJfrArrNull> g_urma("urma_0439");

bool Urma0439UrmaCmdDeleteJfrBatchInvalidParamJfrArrNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0439UrmaCmdDeleteJfrBatchInvalidParamJfrArrNull::GetName() const
{
    return "urma_cmd_delete_jfr_batch 参数非法（jfr_arr == NULL || jfr_num <= 0 || bad_jfr == NULL）";
}

std::string Urma0439UrmaCmdDeleteJfrBatchInvalidParamJfrArrNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr_arr == NULL || jfr_num <= 0 || bad_jfr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0439UrmaCmdDeleteJfrBatchInvalidParamJfrArrNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0439UrmaCmdDeleteJfrBatchInvalidParamJfrArrNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0439UrmaCmdDeleteJfrBatchInvalidParamJfrArrNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0439UrmaCmdDeleteJfrBatchInvalidParamJfrArrNull::GetId() const
{
    return "urma_0439";
}
} // namespace diag
