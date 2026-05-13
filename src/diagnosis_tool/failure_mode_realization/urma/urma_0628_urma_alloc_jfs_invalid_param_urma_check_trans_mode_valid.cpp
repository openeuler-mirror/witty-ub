#include "urma_0628_urma_alloc_jfs_invalid_param_urma_check_trans_mode_valid.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0628UrmaAllocJfsInvalidParamUrmaCheckTransModeValid> g_urma("urma_0628");

bool Urma0628UrmaAllocJfsInvalidParamUrmaCheckTransModeValid::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, trans_mode: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0628UrmaAllocJfsInvalidParamUrmaCheckTransModeValid::GetName() const
{
    return "urma_alloc_jfs 参数非法（urma_check_trans_mode_valid(cfg->trans_mode) != true）";
}

std::string Urma0628UrmaAllocJfsInvalidParamUrmaCheckTransModeValid::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `urma_check_trans_mode_valid(cfg->trans_mode) != true`；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0628UrmaAllocJfsInvalidParamUrmaCheckTransModeValid::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0628UrmaAllocJfsInvalidParamUrmaCheckTransModeValid::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0628UrmaAllocJfsInvalidParamUrmaCheckTransModeValid::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, trans_mode: %.";
}

std::string Urma0628UrmaAllocJfsInvalidParamUrmaCheckTransModeValid::GetId() const
{
    return "urma_0628";
}
} // namespace diag
