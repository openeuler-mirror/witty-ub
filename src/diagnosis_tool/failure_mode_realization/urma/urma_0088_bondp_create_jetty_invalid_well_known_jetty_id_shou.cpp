#include "urma_0088_bondp_create_jetty_invalid_well_known_jetty_id_shou.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0088BondpCreateJettyInvalidWellKnownJettyIdShou> g_urma("urma_0088");

bool Urma0088BondpCreateJettyInvalidWellKnownJettyIdShou::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid well known jetty id: %, should be in (0, 1024)"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0088BondpCreateJettyInvalidWellKnownJettyIdShou::GetName() const
{
    return "bondp_create_jetty Invalid well known jetty id: %, shou";
}

std::string Urma0088BondpCreateJettyInvalidWellKnownJettyIdShou::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `jetty_cfg->id >= BONDP_MAX_WELL_KNOWN_JETTY_ID`；该路径返回 NULL";
}

RootCause Urma0088BondpCreateJettyInvalidWellKnownJettyIdShou::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0088BondpCreateJettyInvalidWellKnownJettyIdShou::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0088BondpCreateJettyInvalidWellKnownJettyIdShou::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid well known jetty id: %, should be in (0, 1024)";
}

std::string Urma0088BondpCreateJettyInvalidWellKnownJettyIdShou::GetId() const
{
    return "urma_0088";
}
} // namespace diag
