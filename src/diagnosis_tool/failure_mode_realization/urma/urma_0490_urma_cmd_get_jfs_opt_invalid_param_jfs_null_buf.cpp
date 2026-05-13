#include "urma_0490_urma_cmd_get_jfs_opt_invalid_param_jfs_null_buf.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0490UrmaCmdGetJfsOptInvalidParamJfsNullBuf> g_urma("urma_0490");

bool Urma0490UrmaCmdGetJfsOptInvalidParamJfsNullBuf::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0490UrmaCmdGetJfsOptInvalidParamJfsNullBuf::GetName() const
{
    return "urma_cmd_get_jfs_opt 参数非法（jfs == NULL || buf == NULL || opt == 0 || len == 0）";
}

std::string Urma0490UrmaCmdGetJfsOptInvalidParamJfsNullBuf::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL || buf == NULL || opt == 0 || len == 0`；该路径返回 -1";
}

RootCause Urma0490UrmaCmdGetJfsOptInvalidParamJfsNullBuf::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0490UrmaCmdGetJfsOptInvalidParamJfsNullBuf::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0490UrmaCmdGetJfsOptInvalidParamJfsNullBuf::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0490UrmaCmdGetJfsOptInvalidParamJfsNullBuf::GetId() const
{
    return "urma_0490";
}
} // namespace diag
