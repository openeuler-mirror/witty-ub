#include "urma_0624_urma_alloc_jfr_invalid_param_urma_check_trans_mode_valid.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0624UrmaAllocJfrInvalidParamUrmaCheckTransModeValid> g_urma("urma_0624");

bool Urma0624UrmaAllocJfrInvalidParamUrmaCheckTransModeValid::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, trans_mode: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0624UrmaAllocJfrInvalidParamUrmaCheckTransModeValid::GetName() const
{
    return "urma_alloc_jfr 参数非法（urma_check_trans_mode_valid(cfg->trans_mode) != true）";
}

std::string Urma0624UrmaAllocJfrInvalidParamUrmaCheckTransModeValid::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `urma_check_trans_mode_valid(cfg->trans_mode) != true`；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0624UrmaAllocJfrInvalidParamUrmaCheckTransModeValid::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0624UrmaAllocJfrInvalidParamUrmaCheckTransModeValid::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0624UrmaAllocJfrInvalidParamUrmaCheckTransModeValid::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, trans_mode: %.";
}

std::string Urma0624UrmaAllocJfrInvalidParamUrmaCheckTransModeValid::GetId() const
{
    return "urma_0624";
}
} // namespace diag
