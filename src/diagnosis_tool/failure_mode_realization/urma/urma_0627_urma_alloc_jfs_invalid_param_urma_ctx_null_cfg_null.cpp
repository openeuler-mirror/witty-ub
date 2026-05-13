#include "urma_0627_urma_alloc_jfs_invalid_param_urma_ctx_null_cfg_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0627UrmaAllocJfsInvalidParamUrmaCtxNullCfgNull> g_urma("urma_0627");

bool Urma0627UrmaAllocJfsInvalidParamUrmaCtxNullCfgNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0627UrmaAllocJfsInvalidParamUrmaCtxNullCfgNull::GetName() const
{
    return "urma_alloc_jfs 参数非法（urma_ctx == NULL || cfg == NULL || jfs == NULL || cfg->jfc == NULL）";
}

std::string Urma0627UrmaAllocJfsInvalidParamUrmaCtxNullCfgNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `urma_ctx == NULL || cfg == NULL || jfs == NULL || cfg->jfc == "
           "NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0627UrmaAllocJfsInvalidParamUrmaCtxNullCfgNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0627UrmaAllocJfsInvalidParamUrmaCtxNullCfgNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0627UrmaAllocJfsInvalidParamUrmaCtxNullCfgNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0627UrmaAllocJfsInvalidParamUrmaCtxNullCfgNull::GetId() const
{
    return "urma_0627";
}
} // namespace diag
