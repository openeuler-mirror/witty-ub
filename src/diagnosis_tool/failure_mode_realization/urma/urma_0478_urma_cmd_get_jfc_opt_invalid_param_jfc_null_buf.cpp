#include "urma_0478_urma_cmd_get_jfc_opt_invalid_param_jfc_null_buf.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0478UrmaCmdGetJfcOptInvalidParamJfcNullBuf> g_urma("urma_0478");

bool Urma0478UrmaCmdGetJfcOptInvalidParamJfcNullBuf::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0478UrmaCmdGetJfcOptInvalidParamJfcNullBuf::GetName() const
{
    return "urma_cmd_get_jfc_opt 参数非法（jfc == NULL || buf == NULL || opt == 0 || len == 0）";
}

std::string Urma0478UrmaCmdGetJfcOptInvalidParamJfcNullBuf::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL || buf == NULL || opt == 0 || len == 0`；该路径返回 -1";
}

RootCause Urma0478UrmaCmdGetJfcOptInvalidParamJfcNullBuf::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0478UrmaCmdGetJfcOptInvalidParamJfcNullBuf::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0478UrmaCmdGetJfcOptInvalidParamJfcNullBuf::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0478UrmaCmdGetJfcOptInvalidParamJfcNullBuf::GetId() const
{
    return "urma_0478";
}
} // namespace diag
