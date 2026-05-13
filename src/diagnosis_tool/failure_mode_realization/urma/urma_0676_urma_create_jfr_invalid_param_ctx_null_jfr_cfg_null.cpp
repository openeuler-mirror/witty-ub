#include "urma_0676_urma_create_jfr_invalid_param_ctx_null_jfr_cfg_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0676UrmaCreateJfrInvalidParamCtxNullJfrCfgNull> g_urma("urma_0676");

bool Urma0676UrmaCreateJfrInvalidParamCtxNullJfrCfgNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0676UrmaCreateJfrInvalidParamCtxNullJfrCfgNull::GetName() const
{
    return "urma_create_jfr 参数非法（ctx == NULL || jfr_cfg == NULL || jfr_cfg->jfc == NULL）";
}

std::string Urma0676UrmaCreateJfrInvalidParamCtxNullJfrCfgNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || jfr_cfg == NULL || jfr_cfg->jfc == NULL`；该路径返回 NULL";
}

RootCause Urma0676UrmaCreateJfrInvalidParamCtxNullJfrCfgNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0676UrmaCreateJfrInvalidParamCtxNullJfrCfgNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0676UrmaCreateJfrInvalidParamCtxNullJfrCfgNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0676UrmaCreateJfrInvalidParamCtxNullJfrCfgNull::GetId() const
{
    return "urma_0676";
}
} // namespace diag
