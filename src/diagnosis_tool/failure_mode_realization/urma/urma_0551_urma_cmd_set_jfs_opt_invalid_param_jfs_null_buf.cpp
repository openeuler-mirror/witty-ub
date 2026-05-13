#include "urma_0551_urma_cmd_set_jfs_opt_invalid_param_jfs_null_buf.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0551UrmaCmdSetJfsOptInvalidParamJfsNullBuf> g_urma("urma_0551");

bool Urma0551UrmaCmdSetJfsOptInvalidParamJfsNullBuf::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0551UrmaCmdSetJfsOptInvalidParamJfsNullBuf::GetName() const
{
    return "urma_cmd_set_jfs_opt 参数非法（jfs == NULL || buf == NULL || opt == 0 || len == 0）";
}

std::string Urma0551UrmaCmdSetJfsOptInvalidParamJfsNullBuf::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL || buf == NULL || opt == 0 || len == 0`；该路径返回 -1";
}

RootCause Urma0551UrmaCmdSetJfsOptInvalidParamJfsNullBuf::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0551UrmaCmdSetJfsOptInvalidParamJfsNullBuf::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0551UrmaCmdSetJfsOptInvalidParamJfsNullBuf::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0551UrmaCmdSetJfsOptInvalidParamJfsNullBuf::GetId() const
{
    return "urma_0551";
}
} // namespace diag
