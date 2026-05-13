#include "urma_0089_bondp_create_jetty_matrix_server_jetty_only_support.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0089BondpCreateJettyMatrixServerJettyOnlySupport> g_urma("urma_0089");

bool Urma0089BondpCreateJettyMatrixServerJettyOnlySupport::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"In matrix server, jetty only supports single-path mode with RC."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0089BondpCreateJettyMatrixServerJettyOnlySupport::GetName() const
{
    return "bondp_create_jetty In matrix server, jetty only support";
}

std::string Urma0089BondpCreateJettyMatrixServerJettyOnlySupport::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `jetty_cfg->jfs_cfg.trans_mode != URMA_TM_RC`；该路径返回 NULL";
}

RootCause Urma0089BondpCreateJettyMatrixServerJettyOnlySupport::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0089BondpCreateJettyMatrixServerJettyOnlySupport::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0089BondpCreateJettyMatrixServerJettyOnlySupport::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：In matrix server, jetty only supports single-path mode with RC.";
}

std::string Urma0089BondpCreateJettyMatrixServerJettyOnlySupport::GetId() const
{
    return "urma_0089";
}
} // namespace diag
