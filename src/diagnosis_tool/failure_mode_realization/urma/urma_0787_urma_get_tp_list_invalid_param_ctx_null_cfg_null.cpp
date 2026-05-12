#include "urma_0787_urma_get_tp_list_invalid_param_ctx_null_cfg_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0787UrmaGetTpListInvalidParamCtxNullCfgNull> g_urma("urma_0787");

bool Urma0787UrmaGetTpListInvalidParamCtxNullCfgNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0787UrmaGetTpListInvalidParamCtxNullCfgNull::GetName() const
{
    return "urma_get_tp_list 参数非法（ctx == NULL || cfg == NULL || tp_cnt == NULL || tp_list == NULL || *tp_cnt == "
           "0）";
}

std::string Urma0787UrmaGetTpListInvalidParamCtxNullCfgNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || cfg == NULL || tp_cnt == NULL || tp_list == NULL || *tp_cnt "
           "== 0`；该路径返回 URMA_EINVAL";
}

RootCause Urma0787UrmaGetTpListInvalidParamCtxNullCfgNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0787UrmaGetTpListInvalidParamCtxNullCfgNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0787UrmaGetTpListInvalidParamCtxNullCfgNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0787UrmaGetTpListInvalidParamCtxNullCfgNull::GetId() const
{
    return "urma_0787";
}
} // namespace diag
