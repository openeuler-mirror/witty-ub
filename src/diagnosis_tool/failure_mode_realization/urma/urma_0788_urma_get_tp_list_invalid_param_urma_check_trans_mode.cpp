#include "urma_0788_urma_get_tp_list_invalid_param_urma_check_trans_mode.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0788UrmaGetTpListInvalidParamUrmaCheckTransMode> g_urma("urma_0788");

bool Urma0788UrmaGetTpListInvalidParamUrmaCheckTransMode::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, trans_mode: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0788UrmaGetTpListInvalidParamUrmaCheckTransMode::GetName() const
{
    return "urma_get_tp_list 参数非法（urma_check_trans_mode_valid(cfg->trans_mode) != true）";
}

std::string Urma0788UrmaGetTpListInvalidParamUrmaCheckTransMode::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `urma_check_trans_mode_valid(cfg->trans_mode) != true`；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0788UrmaGetTpListInvalidParamUrmaCheckTransMode::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0788UrmaGetTpListInvalidParamUrmaCheckTransMode::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0788UrmaGetTpListInvalidParamUrmaCheckTransMode::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, trans_mode: %.";
}

std::string Urma0788UrmaGetTpListInvalidParamUrmaCheckTransMode::GetId() const
{
    return "urma_0788";
}
} // namespace diag
