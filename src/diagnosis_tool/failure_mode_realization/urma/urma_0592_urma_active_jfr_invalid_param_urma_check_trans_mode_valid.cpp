#include "urma_0592_urma_active_jfr_invalid_param_urma_check_trans_mode_valid.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0592UrmaActiveJfrInvalidParamUrmaCheckTransModeValid> g_urma("urma_0592");

bool Urma0592UrmaActiveJfrInvalidParamUrmaCheckTransModeValid::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, trans_mode: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0592UrmaActiveJfrInvalidParamUrmaCheckTransModeValid::GetName() const
{
    return "urma_active_jfr 参数非法（urma_check_trans_mode_valid(cfg->trans_mode) != true）";
}

std::string Urma0592UrmaActiveJfrInvalidParamUrmaCheckTransModeValid::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `urma_check_trans_mode_valid(cfg->trans_mode) != true`；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0592UrmaActiveJfrInvalidParamUrmaCheckTransModeValid::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0592UrmaActiveJfrInvalidParamUrmaCheckTransModeValid::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0592UrmaActiveJfrInvalidParamUrmaCheckTransModeValid::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, trans_mode: %.";
}

std::string Urma0592UrmaActiveJfrInvalidParamUrmaCheckTransModeValid::GetId() const
{
    return "urma_0592";
}
} // namespace diag
