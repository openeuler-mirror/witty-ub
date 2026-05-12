#include "urma_0704_urma_delete_jetty_resource_delete_failure_jetty_cfg_jfs_cfg.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0704UrmaDeleteJettyResourceDeleteFailureJettyCfgJfsCfg> g_urma("urma_0704");

bool Urma0704UrmaDeleteJettyResourceDeleteFailureJettyCfgJfsCfg::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete jetty because it has remote jetty, try unbind first"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0704UrmaDeleteJettyResourceDeleteFailureJettyCfgJfsCfg::GetName() const
{
    return "urma_delete_jetty 删除资源失败（jetty->jetty_cfg.jfs_cfg.trans_mode == URMA_TM_RC && jetty->remote_jetty "
           "!= NULL）";
}

std::string Urma0704UrmaDeleteJettyResourceDeleteFailureJettyCfgJfsCfg::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_ENOPERM";
}

RootCause Urma0704UrmaDeleteJettyResourceDeleteFailureJettyCfgJfsCfg::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0704UrmaDeleteJettyResourceDeleteFailureJettyCfgJfsCfg::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0704UrmaDeleteJettyResourceDeleteFailureJettyCfgJfsCfg::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete jetty because it has remote jetty, try unbind "
           "first";
}

std::string Urma0704UrmaDeleteJettyResourceDeleteFailureJettyCfgJfsCfg::GetId() const
{
    return "urma_0704";
}
} // namespace diag
