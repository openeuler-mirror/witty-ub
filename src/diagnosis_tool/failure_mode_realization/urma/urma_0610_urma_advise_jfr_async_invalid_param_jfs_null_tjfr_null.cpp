#include "urma_0610_urma_advise_jfr_async_invalid_param_jfs_null_tjfr_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0610UrmaAdviseJfrAsyncInvalidParamJfsNullTjfrNull> g_urma("urma_0610");

bool Urma0610UrmaAdviseJfrAsyncInvalidParamJfsNullTjfrNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0610UrmaAdviseJfrAsyncInvalidParamJfsNullTjfrNull::GetName() const
{
    return "urma_advise_jfr_async 参数非法（jfs == NULL || tjfr == NULL || (jfs->jfs_cfg.trans_mode != URMA_TM_RM || "
           "tjfr->trans_mode != URMA_TM）";
}

std::string Urma0610UrmaAdviseJfrAsyncInvalidParamJfsNullTjfrNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL || tjfr == NULL || (jfs->jfs_cfg.trans_mode != URMA_TM_RM || "
           "tjfr->trans_mode != URMA_TM`；该路径返回 URMA_EINVAL";
}

RootCause Urma0610UrmaAdviseJfrAsyncInvalidParamJfsNullTjfrNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0610UrmaAdviseJfrAsyncInvalidParamJfsNullTjfrNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0610UrmaAdviseJfrAsyncInvalidParamJfsNullTjfrNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0610UrmaAdviseJfrAsyncInvalidParamJfsNullTjfrNull::GetId() const
{
    return "urma_0610";
}
} // namespace diag
