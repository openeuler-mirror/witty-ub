#include "urma_0158_bondp_import_jetty_multi_path_jetty_only_support_ctp_t.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0158BondpImportJettyMultiPathJettyOnlySupportCtpT> g_urma("urma_0158");

bool Urma0158BondpImportJettyMultiPathJettyOnlySupportCtpT::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Multi-path jetty only support CTP, tp_type:%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0158BondpImportJettyMultiPathJettyOnlySupportCtpT::GetName() const
{
    return "bondp_import_jetty Multi-path jetty only support CTP, t";
}

std::string Urma0158BondpImportJettyMultiPathJettyOnlySupportCtpT::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `rjetty->tp_type != URMA_CTP`";
}

RootCause Urma0158BondpImportJettyMultiPathJettyOnlySupportCtpT::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0158BondpImportJettyMultiPathJettyOnlySupportCtpT::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0158BondpImportJettyMultiPathJettyOnlySupportCtpT::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Multi-path jetty only support CTP, tp_type:%";
}

std::string Urma0158BondpImportJettyMultiPathJettyOnlySupportCtpT::GetId() const
{
    return "urma_0158";
}
} // namespace diag
