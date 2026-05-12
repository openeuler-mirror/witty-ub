#include "urma_0850_urma_unadvise_jfr_invalid_param_ops_null_ops_unadvise_jfr.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0850UrmaUnadviseJfrInvalidParamOpsNullOpsUnadviseJfr> g_urma("urma_0850");

bool Urma0850UrmaUnadviseJfrInvalidParamOpsNullOpsUnadviseJfr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0850UrmaUnadviseJfrInvalidParamOpsNullOpsUnadviseJfr::GetName() const
{
    return "urma_unadvise_jfr 参数非法（ops == NULL || ops->unadvise_jfr == NULL）";
}

std::string Urma0850UrmaUnadviseJfrInvalidParamOpsNullOpsUnadviseJfr::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ops == NULL || ops->unadvise_jfr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0850UrmaUnadviseJfrInvalidParamOpsNullOpsUnadviseJfr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0850UrmaUnadviseJfrInvalidParamOpsNullOpsUnadviseJfr::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0850UrmaUnadviseJfrInvalidParamOpsNullOpsUnadviseJfr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0850UrmaUnadviseJfrInvalidParamOpsNullOpsUnadviseJfr::GetId() const
{
    return "urma_0850";
}
} // namespace diag
