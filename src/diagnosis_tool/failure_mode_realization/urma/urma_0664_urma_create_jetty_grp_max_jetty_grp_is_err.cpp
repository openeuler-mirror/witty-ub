#include "urma_0664_urma_create_jetty_grp_max_jetty_grp_is_err.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0664UrmaCreateJettyGrpMaxJettyGrpIsErr> g_urma("urma_0664");

bool Urma0664UrmaCreateJettyGrpMaxJettyGrpIsErr::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"max_jetty_in_jetty_grp % is err."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0664UrmaCreateJettyGrpMaxJettyGrpIsErr::GetName() const
{
    return "urma_create_jetty_grp max_jetty_in_jetty_grp % is err.";
}

std::string Urma0664UrmaCreateJettyGrpMaxJettyGrpIsErr::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `max_jetty_in_jetty_grp == 0 || max_jetty_in_jetty_grp > "
           "URMA_MAX_JETTY_IN_JETTY_GRP`；该路径返回 NULL";
}

RootCause Urma0664UrmaCreateJettyGrpMaxJettyGrpIsErr::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0664UrmaCreateJettyGrpMaxJettyGrpIsErr::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0664UrmaCreateJettyGrpMaxJettyGrpIsErr::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：max_jetty_in_jetty_grp % is err.";
}

std::string Urma0664UrmaCreateJettyGrpMaxJettyGrpIsErr::GetId() const
{
    return "urma_0664";
}
} // namespace diag
