#include "urma_0484_urma_cmd_get_jfr_opt_invalid_param_jfr_null_buf.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0484UrmaCmdGetJfrOptInvalidParamJfrNullBuf> g_urma("urma_0484");

bool Urma0484UrmaCmdGetJfrOptInvalidParamJfrNullBuf::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0484UrmaCmdGetJfrOptInvalidParamJfrNullBuf::GetName() const
{
    return "urma_cmd_get_jfr_opt 参数非法（jfr == NULL || buf == NULL || opt == 0 || len == 0）";
}

std::string Urma0484UrmaCmdGetJfrOptInvalidParamJfrNullBuf::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL || buf == NULL || opt == 0 || len == 0`；该路径返回 -1";
}

RootCause Urma0484UrmaCmdGetJfrOptInvalidParamJfrNullBuf::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0484UrmaCmdGetJfrOptInvalidParamJfrNullBuf::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0484UrmaCmdGetJfrOptInvalidParamJfrNullBuf::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0484UrmaCmdGetJfrOptInvalidParamJfrNullBuf::GetId() const
{
    return "urma_0484";
}
} // namespace diag
