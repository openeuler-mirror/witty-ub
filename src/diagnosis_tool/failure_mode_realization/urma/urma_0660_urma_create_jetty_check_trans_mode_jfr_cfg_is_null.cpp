#include "urma_0660_urma_create_jetty_check_trans_mode_jfr_cfg_is_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0660UrmaCreateJettyCheckTransModeJfrCfgIsNull> g_urma("urma_0660");

bool Urma0660UrmaCreateJettyCheckTransModeJfrCfgIsNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "jfr cfg is null or trans_mode or order_type invalid with non shared jfr flag."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0660UrmaCreateJettyCheckTransModeJfrCfgIsNull::GetName() const
{
    return "urma_create_jetty_check_trans_mode jfr cfg is null or trans_mode or ord";
}

std::string Urma0660UrmaCreateJettyCheckTransModeJfrCfgIsNull::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `jetty_cfg->flag.bs.share_jfr == URMA_NO_SHARE_JFR && (jetty_cfg->jfr_cfg == NULL || "
           "urma_check_trans`；该路径返回 -1";
}

RootCause Urma0660UrmaCreateJettyCheckTransModeJfrCfgIsNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0660UrmaCreateJettyCheckTransModeJfrCfgIsNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0660UrmaCreateJettyCheckTransModeJfrCfgIsNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfr cfg is null or trans_mode or order_type invalid with non "
           "shared jfr flag.";
}

std::string Urma0660UrmaCreateJettyCheckTransModeJfrCfgIsNull::GetId() const
{
    return "urma_0660";
}
} // namespace diag
