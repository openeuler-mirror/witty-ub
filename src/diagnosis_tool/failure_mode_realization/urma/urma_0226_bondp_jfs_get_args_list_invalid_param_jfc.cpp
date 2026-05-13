#include "urma_0226_bondp_jfs_get_args_list_invalid_param_jfc.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0226BondpJfsGetArgsListInvalidParamJfc> g_urma("urma_0226");

bool Urma0226BondpJfsGetArgsListInvalidParamJfc::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param jfc"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0226BondpJfsGetArgsListInvalidParamJfc::GetName() const
{
    return "bondp_jfs_get_args_list Invalid param jfc";
}

std::string Urma0226BondpJfsGetArgsListInvalidParamJfc::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bondp_comp(bdp_jfc)`；该路径返回 NULL";
}

RootCause Urma0226BondpJfsGetArgsListInvalidParamJfc::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0226BondpJfsGetArgsListInvalidParamJfc::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0226BondpJfsGetArgsListInvalidParamJfc::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param jfc";
}

std::string Urma0226BondpJfsGetArgsListInvalidParamJfc::GetId() const
{
    return "urma_0226";
}
} // namespace diag
