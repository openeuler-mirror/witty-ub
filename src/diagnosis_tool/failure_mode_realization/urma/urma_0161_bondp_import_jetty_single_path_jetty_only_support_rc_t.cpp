#include "urma_0161_bondp_import_jetty_single_path_jetty_only_support_rc_t.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0161BondpImportJettySinglePathJettyOnlySupportRcT> g_urma("urma_0161");

bool Urma0161BondpImportJettySinglePathJettyOnlySupportRcT::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Single-path jetty only support RC, trans_mode:%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0161BondpImportJettySinglePathJettyOnlySupportRcT::GetName() const
{
    return "bondp_import_jetty Single-path jetty only support RC, t";
}

std::string Urma0161BondpImportJettySinglePathJettyOnlySupportRcT::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `rjetty->trans_mode != URMA_TM_RC`";
}

RootCause Urma0161BondpImportJettySinglePathJettyOnlySupportRcT::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0161BondpImportJettySinglePathJettyOnlySupportRcT::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0161BondpImportJettySinglePathJettyOnlySupportRcT::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Single-path jetty only support RC, trans_mode:%";
}

std::string Urma0161BondpImportJettySinglePathJettyOnlySupportRcT::GetId() const
{
    return "urma_0161";
}
} // namespace diag
