#include "urma_0526_urma_cmd_query_jetty_invalid_param_cfg_jfr_cfg_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0526UrmaCmdQueryJettyInvalidParamCfgJfrCfgNull> g_urma("urma_0526");

bool Urma0526UrmaCmdQueryJettyInvalidParamCfgJfrCfgNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0526UrmaCmdQueryJettyInvalidParamCfgJfrCfgNull::GetName() const
{
    return "urma_cmd_query_jetty 参数非法（cfg->jfr_cfg == NULL）";
}

std::string Urma0526UrmaCmdQueryJettyInvalidParamCfgJfrCfgNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `cfg->jfr_cfg == NULL`；该路径返回 -1";
}

RootCause Urma0526UrmaCmdQueryJettyInvalidParamCfgJfrCfgNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0526UrmaCmdQueryJettyInvalidParamCfgJfrCfgNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0526UrmaCmdQueryJettyInvalidParamCfgJfrCfgNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0526UrmaCmdQueryJettyInvalidParamCfgJfrCfgNull::GetId() const
{
    return "urma_0526";
}
} // namespace diag
