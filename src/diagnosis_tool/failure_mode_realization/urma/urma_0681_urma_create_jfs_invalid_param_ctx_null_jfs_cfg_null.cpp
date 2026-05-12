#include "urma_0681_urma_create_jfs_invalid_param_ctx_null_jfs_cfg_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0681UrmaCreateJfsInvalidParamCtxNullJfsCfgNull> g_urma("urma_0681");

bool Urma0681UrmaCreateJfsInvalidParamCtxNullJfsCfgNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0681UrmaCreateJfsInvalidParamCtxNullJfsCfgNull::GetName() const
{
    return "urma_create_jfs 参数非法（ctx == NULL || jfs_cfg == NULL || jfs_cfg->jfc == NULL）";
}

std::string Urma0681UrmaCreateJfsInvalidParamCtxNullJfsCfgNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || jfs_cfg == NULL || jfs_cfg->jfc == NULL`；该路径返回 NULL";
}

RootCause Urma0681UrmaCreateJfsInvalidParamCtxNullJfsCfgNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0681UrmaCreateJfsInvalidParamCtxNullJfsCfgNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0681UrmaCreateJfsInvalidParamCtxNullJfsCfgNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0681UrmaCreateJfsInvalidParamCtxNullJfsCfgNull::GetId() const
{
    return "urma_0681";
}
} // namespace diag
