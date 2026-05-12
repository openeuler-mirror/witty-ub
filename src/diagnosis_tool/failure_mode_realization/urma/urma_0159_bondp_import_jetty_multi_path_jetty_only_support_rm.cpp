#include "urma_0159_bondp_import_jetty_multi_path_jetty_only_support_rm.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0159BondpImportJettyMultiPathJettyOnlySupportRm> g_urma("urma_0159");

bool Urma0159BondpImportJettyMultiPathJettyOnlySupportRm::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Multi-path jetty only support RM or RC, trans_mode:%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0159BondpImportJettyMultiPathJettyOnlySupportRm::GetName() const
{
    return "bondp_import_jetty Multi-path jetty only support RM or";
}

std::string Urma0159BondpImportJettyMultiPathJettyOnlySupportRm::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `rjetty->trans_mode != URMA_TM_RM && rjetty->trans_mode != URMA_TM_RC`";
}

RootCause Urma0159BondpImportJettyMultiPathJettyOnlySupportRm::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0159BondpImportJettyMultiPathJettyOnlySupportRm::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0159BondpImportJettyMultiPathJettyOnlySupportRm::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Multi-path jetty only support RM or RC, trans_mode:%";
}

std::string Urma0159BondpImportJettyMultiPathJettyOnlySupportRm::GetId() const
{
    return "urma_0159";
}
} // namespace diag
