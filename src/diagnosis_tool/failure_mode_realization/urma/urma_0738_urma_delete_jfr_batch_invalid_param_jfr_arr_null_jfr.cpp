#include "urma_0738_urma_delete_jfr_batch_invalid_param_jfr_arr_null_jfr.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0738UrmaDeleteJfrBatchInvalidParamJfrArrNullJfr> g_urma("urma_0738");

bool Urma0738UrmaDeleteJfrBatchInvalidParamJfrArrNullJfr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0738UrmaDeleteJfrBatchInvalidParamJfrArrNullJfr::GetName() const
{
    return "urma_delete_jfr_batch 参数非法（jfr_arr == NULL || jfr_num <= 0 || bad_jfr == NULL）";
}

std::string Urma0738UrmaDeleteJfrBatchInvalidParamJfrArrNullJfr::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr_arr == NULL || jfr_num <= 0 || bad_jfr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0738UrmaDeleteJfrBatchInvalidParamJfrArrNullJfr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0738UrmaDeleteJfrBatchInvalidParamJfrArrNullJfr::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0738UrmaDeleteJfrBatchInvalidParamJfrArrNullJfr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0738UrmaDeleteJfrBatchInvalidParamJfrArrNullJfr::GetId() const
{
    return "urma_0738";
}
} // namespace diag
