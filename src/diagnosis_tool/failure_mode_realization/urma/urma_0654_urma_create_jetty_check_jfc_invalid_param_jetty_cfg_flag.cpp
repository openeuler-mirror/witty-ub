#include "urma_0654_urma_create_jetty_check_jfc_invalid_param_jetty_cfg_flag.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0654UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag> g_urma("urma_0654");

bool Urma0654UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "Invalid parameter, jfr cfg is null or jfc is NULL with non shared jfr flag."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0654UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag::GetName() const
{
    return "urma_create_jetty_check_jfc 参数非法（jetty_cfg->flag.bs.share_jfr == URMA_NO_SHARE_JFR && "
           "(jetty_cfg->jfr_cfg == NULL || jetty_cfg->jfr_c）";
}

std::string Urma0654UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty_cfg->flag.bs.share_jfr == URMA_NO_SHARE_JFR && (jetty_cfg->jfr_cfg == "
           "NULL || jetty_cfg->jfr_c`；该路径返回 -1";
}

RootCause Urma0654UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0654UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0654UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, jfr cfg is null or jfc is NULL with non shared "
           "jfr flag.";
}

std::string Urma0654UrmaCreateJettyCheckJfcInvalidParamJettyCfgFlag::GetId() const
{
    return "urma_0654";
}
} // namespace diag
