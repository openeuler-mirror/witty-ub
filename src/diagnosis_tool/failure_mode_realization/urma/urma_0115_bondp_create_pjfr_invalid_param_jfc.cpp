#include "urma_0115_bondp_create_pjfr_invalid_param_jfc.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0115BondpCreatePjfrInvalidParamJfc> g_urma("urma_0115");

bool Urma0115BondpCreatePjfrInvalidParamJfc::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param jfc"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0115BondpCreatePjfrInvalidParamJfc::GetName() const
{
    return "bondp_create_pjfr Invalid param jfc";
}

std::string Urma0115BondpCreatePjfrInvalidParamJfc::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bondp_comp(bdp_jfc)`；该路径返回 -1";
}

RootCause Urma0115BondpCreatePjfrInvalidParamJfc::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0115BondpCreatePjfrInvalidParamJfc::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0115BondpCreatePjfrInvalidParamJfc::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param jfc";
}

std::string Urma0115BondpCreatePjfrInvalidParamJfc::GetId() const
{
    return "urma_0115";
}
} // namespace diag
