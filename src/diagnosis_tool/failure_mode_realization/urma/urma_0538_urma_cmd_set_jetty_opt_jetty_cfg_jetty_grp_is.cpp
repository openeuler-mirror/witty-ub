#include "urma_0538_urma_cmd_set_jetty_opt_jetty_cfg_jetty_grp_is.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0538UrmaCmdSetJettyOptJettyCfgJettyGrpIs> g_urma("urma_0538");

bool Urma0538UrmaCmdSetJettyOptJettyCfgJettyGrpIs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jetty->jetty_cfg.jetty_grp is not exist"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0538UrmaCmdSetJettyOptJettyCfgJettyGrpIs::GetName() const
{
    return "urma_cmd_set_jetty_opt jetty->jetty_cfg.jetty_grp is not ex";
}

std::string Urma0538UrmaCmdSetJettyOptJettyCfgJettyGrpIs::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 "
           "-1";
}

RootCause Urma0538UrmaCmdSetJettyOptJettyCfgJettyGrpIs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0538UrmaCmdSetJettyOptJettyCfgJettyGrpIs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0538UrmaCmdSetJettyOptJettyCfgJettyGrpIs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jetty->jetty_cfg.jetty_grp is not exist";
}

std::string Urma0538UrmaCmdSetJettyOptJettyCfgJettyGrpIs::GetId() const
{
    return "urma_0538";
}
} // namespace diag
