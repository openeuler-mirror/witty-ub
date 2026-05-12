#include "urma_0087_bondp_create_jetty_create_jetty_failure_jetty_cfg_flag_bs.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0087BondpCreateJettyCreateJettyFailureJettyCfgFlagBs> g_urma("urma_0087");

bool Urma0087BondpCreateJettyCreateJettyFailureJettyCfgFlagBs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"UB device must use shared jfr when create jetty."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0087BondpCreateJettyCreateJettyFailureJettyCfgFlagBs::GetName() const
{
    return "bondp_create_jetty 创建Jetty失败（jetty_cfg->flag.bs.share_jfr != true || jetty_cfg->shared.jfr == NULL）";
}

std::string Urma0087BondpCreateJettyCreateJettyFailureJettyCfgFlagBs::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma0087BondpCreateJettyCreateJettyFailureJettyCfgFlagBs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0087BondpCreateJettyCreateJettyFailureJettyCfgFlagBs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0087BondpCreateJettyCreateJettyFailureJettyCfgFlagBs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：UB device must use shared jfr when create jetty.";
}

std::string Urma0087BondpCreateJettyCreateJettyFailureJettyCfgFlagBs::GetId() const
{
    return "urma_0087";
}
} // namespace diag
