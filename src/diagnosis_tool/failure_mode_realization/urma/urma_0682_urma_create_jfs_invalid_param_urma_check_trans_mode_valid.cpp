#include "urma_0682_urma_create_jfs_invalid_param_urma_check_trans_mode_valid.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0682UrmaCreateJfsInvalidParamUrmaCheckTransModeValid> g_urma("urma_0682");

bool Urma0682UrmaCreateJfsInvalidParamUrmaCheckTransModeValid::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, trans_mode: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0682UrmaCreateJfsInvalidParamUrmaCheckTransModeValid::GetName() const
{
    return "urma_create_jfs 参数非法（urma_check_trans_mode_valid(jfs_cfg->trans_mode) != true）";
}

std::string Urma0682UrmaCreateJfsInvalidParamUrmaCheckTransModeValid::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `urma_check_trans_mode_valid(jfs_cfg->trans_mode) != true`；该路径返回 NULL";
}

RootCause Urma0682UrmaCreateJfsInvalidParamUrmaCheckTransModeValid::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0682UrmaCreateJfsInvalidParamUrmaCheckTransModeValid::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0682UrmaCreateJfsInvalidParamUrmaCheckTransModeValid::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, trans_mode: %.";
}

std::string Urma0682UrmaCreateJfsInvalidParamUrmaCheckTransModeValid::GetId() const
{
    return "urma_0682";
}
} // namespace diag
