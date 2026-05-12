#include "urma_0623_urma_alloc_jfr_invalid_param_urma_ctx_null_cfg_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0623UrmaAllocJfrInvalidParamUrmaCtxNullCfgNull> g_urma("urma_0623");

bool Urma0623UrmaAllocJfrInvalidParamUrmaCtxNullCfgNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0623UrmaAllocJfrInvalidParamUrmaCtxNullCfgNull::GetName() const
{
    return "urma_alloc_jfr 参数非法（urma_ctx == NULL || cfg == NULL || jfr == NULL || cfg->jfc == NULL）";
}

std::string Urma0623UrmaAllocJfrInvalidParamUrmaCtxNullCfgNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `urma_ctx == NULL || cfg == NULL || jfr == NULL || cfg->jfc == "
           "NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0623UrmaAllocJfrInvalidParamUrmaCtxNullCfgNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0623UrmaAllocJfrInvalidParamUrmaCtxNullCfgNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0623UrmaAllocJfrInvalidParamUrmaCtxNullCfgNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0623UrmaAllocJfrInvalidParamUrmaCtxNullCfgNull::GetId() const
{
    return "urma_0623";
}
} // namespace diag
