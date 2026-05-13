#include "urma_0655_urma_create_jetty_check_jfc_invalid_param_jetty_cfg_flag.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0655UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag> g_urma("urma_0655");

bool Urma0655UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, jfr is null or jfc is NULL with shared jfr flag."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0655UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag::GetName() const
{
    return "urma_create_jetty_check_jfc 参数非法（jetty_cfg->flag.bs.share_jfr == URMA_SHARE_JFR && "
           "(jetty_cfg->shared.jfr == NULL || jetty_cfg->share）";
}

std::string Urma0655UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty_cfg->flag.bs.share_jfr == URMA_SHARE_JFR && (jetty_cfg->shared.jfr == "
           "NULL || jetty_cfg->share`；该路径返回 -1";
}

RootCause Urma0655UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0655UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0655UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, jfr is null or jfc is NULL with shared jfr "
           "flag.";
}

std::string Urma0655UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag::GetId() const
{
    return "urma_0655";
}
} // namespace diag
