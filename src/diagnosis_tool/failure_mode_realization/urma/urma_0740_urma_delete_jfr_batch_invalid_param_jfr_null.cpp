#include "urma_0740_urma_delete_jfr_batch_invalid_param_jfr_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0740UrmaDeleteJfrBatchInvalidParamJfrNull> g_urma("urma_0740");

bool Urma0740UrmaDeleteJfrBatchInvalidParamJfrNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, index: % jfr in the array is NULL."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0740UrmaDeleteJfrBatchInvalidParamJfrNull::GetName() const
{
    return "urma_delete_jfr_batch 参数非法（jfr == NULL）";
}

std::string Urma0740UrmaDeleteJfrBatchInvalidParamJfrNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL`";
}

RootCause Urma0740UrmaDeleteJfrBatchInvalidParamJfrNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0740UrmaDeleteJfrBatchInvalidParamJfrNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0740UrmaDeleteJfrBatchInvalidParamJfrNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, index: % jfr in the array is NULL.";
}

std::string Urma0740UrmaDeleteJfrBatchInvalidParamJfrNull::GetId() const
{
    return "urma_0740";
}
} // namespace diag
