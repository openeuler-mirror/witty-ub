#include "urma_0543_urma_cmd_set_jfc_opt_invalid_param_ctx_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0543UrmaCmdSetJfcOptInvalidParamCtxNull> g_urma("urma_0543");

bool Urma0543UrmaCmdSetJfcOptInvalidParamCtxNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0543UrmaCmdSetJfcOptInvalidParamCtxNull::GetName() const
{
    return "urma_cmd_set_jfc_opt 参数非法（ctx == NULL）";
}

std::string Urma0543UrmaCmdSetJfcOptInvalidParamCtxNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL`；该路径返回 -1";
}

RootCause Urma0543UrmaCmdSetJfcOptInvalidParamCtxNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0543UrmaCmdSetJfcOptInvalidParamCtxNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0543UrmaCmdSetJfcOptInvalidParamCtxNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0543UrmaCmdSetJfcOptInvalidParamCtxNull::GetId() const
{
    return "urma_0543";
}
} // namespace diag
