#include "urma_0849_urma_unadvise_jfr_invalid_param_jfs_null_tjfr_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0849UrmaUnadviseJfrInvalidParamJfsNullTjfrNull> g_urma("urma_0849");

bool Urma0849UrmaUnadviseJfrInvalidParamJfsNullTjfrNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0849UrmaUnadviseJfrInvalidParamJfsNullTjfrNull::GetName() const
{
    return "urma_unadvise_jfr 参数非法（jfs == NULL || tjfr == NULL）";
}

std::string Urma0849UrmaUnadviseJfrInvalidParamJfsNullTjfrNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL || tjfr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0849UrmaUnadviseJfrInvalidParamJfsNullTjfrNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0849UrmaUnadviseJfrInvalidParamJfsNullTjfrNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0849UrmaUnadviseJfrInvalidParamJfsNullTjfrNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0849UrmaUnadviseJfrInvalidParamJfsNullTjfrNull::GetId() const
{
    return "urma_0849";
}
} // namespace diag
