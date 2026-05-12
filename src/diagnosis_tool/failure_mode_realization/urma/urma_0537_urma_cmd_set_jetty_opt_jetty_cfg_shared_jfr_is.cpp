#include "urma_0537_urma_cmd_set_jetty_opt_jetty_cfg_shared_jfr_is.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0537UrmaCmdSetJettyOptJettyCfgSharedJfrIs> g_urma("urma_0537");

bool Urma0537UrmaCmdSetJettyOptJettyCfgSharedJfrIs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jetty->jetty_cfg.shared.jfr is not exist"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0537UrmaCmdSetJettyOptJettyCfgSharedJfrIs::GetName() const
{
    return "urma_cmd_set_jetty_opt jetty->jetty_cfg.shared.jfr is not e";
}

std::string Urma0537UrmaCmdSetJettyOptJettyCfgSharedJfrIs::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 "
           "-1";
}

RootCause Urma0537UrmaCmdSetJettyOptJettyCfgSharedJfrIs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0537UrmaCmdSetJettyOptJettyCfgSharedJfrIs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0537UrmaCmdSetJettyOptJettyCfgSharedJfrIs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jetty->jetty_cfg.shared.jfr is not exist";
}

std::string Urma0537UrmaCmdSetJettyOptJettyCfgSharedJfrIs::GetId() const
{
    return "urma_0537";
}
} // namespace diag
