#include "urma_0216_bondp_jetty_get_args_list_invalid_param_jetty_cfg.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0216BondpJettyGetArgsListInvalidParamJettyCfg> g_urma("urma_0216");

bool Urma0216BondpJettyGetArgsListInvalidParamJettyCfg::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param jetty cfg"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0216BondpJettyGetArgsListInvalidParamJettyCfg::GetName() const
{
    return "bondp_jetty_get_args_list Invalid param jetty cfg";
}

std::string Urma0216BondpJettyGetArgsListInvalidParamJettyCfg::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bondp_comp(bdp_jfs_jfc) || !is_valid_bondp_comp(bdp_jfr) || (bdp_rplc_jfc && "
           "!is_valid_bon`；该路径返回 NULL";
}

RootCause Urma0216BondpJettyGetArgsListInvalidParamJettyCfg::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0216BondpJettyGetArgsListInvalidParamJettyCfg::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0216BondpJettyGetArgsListInvalidParamJettyCfg::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param jetty cfg";
}

std::string Urma0216BondpJettyGetArgsListInvalidParamJettyCfg::GetId() const
{
    return "urma_0216";
}
} // namespace diag
