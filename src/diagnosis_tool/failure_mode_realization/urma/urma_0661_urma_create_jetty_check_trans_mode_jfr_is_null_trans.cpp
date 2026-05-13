#include "urma_0661_urma_create_jetty_check_trans_mode_jfr_is_null_trans.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0661UrmaCreateJettyCheckTransModeJfrIsNullTrans> g_urma("urma_0661");

bool Urma0661UrmaCreateJettyCheckTransModeJfrIsNullTrans::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfr is null or trans_mode or order_type invalid with shared jfr flag."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0661UrmaCreateJettyCheckTransModeJfrIsNullTrans::GetName() const
{
    return "urma_create_jetty_check_trans_mode jfr is null or trans_mode or order_t";
}

std::string Urma0661UrmaCreateJettyCheckTransModeJfrIsNullTrans::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `jetty_cfg->flag.bs.share_jfr == URMA_SHARE_JFR && (jetty_cfg->shared.jfr == NULL || "
           "jetty_cfg->jfs_c`；该路径返回 -1";
}

RootCause Urma0661UrmaCreateJettyCheckTransModeJfrIsNullTrans::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0661UrmaCreateJettyCheckTransModeJfrIsNullTrans::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0661UrmaCreateJettyCheckTransModeJfrIsNullTrans::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfr is null or trans_mode or order_type invalid with shared jfr "
           "flag.";
}

std::string Urma0661UrmaCreateJettyCheckTransModeJfrIsNullTrans::GetId() const
{
    return "urma_0661";
}
} // namespace diag
