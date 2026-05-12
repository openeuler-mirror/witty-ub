#include "urma_0160_bondp_import_jetty_single_path_jetty_only_support_utp_o.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0160BondpImportJettySinglePathJettyOnlySupportUtpO> g_urma("urma_0160");

bool Urma0160BondpImportJettySinglePathJettyOnlySupportUtpO::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Single-path jetty only support UTP or RTP, tp_type:%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0160BondpImportJettySinglePathJettyOnlySupportUtpO::GetName() const
{
    return "bondp_import_jetty Single-path jetty only support UTP o";
}

std::string Urma0160BondpImportJettySinglePathJettyOnlySupportUtpO::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `rjetty->tp_type != URMA_UTP && rjetty->tp_type != URMA_RTP`";
}

RootCause Urma0160BondpImportJettySinglePathJettyOnlySupportUtpO::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0160BondpImportJettySinglePathJettyOnlySupportUtpO::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0160BondpImportJettySinglePathJettyOnlySupportUtpO::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Single-path jetty only support UTP or RTP, tp_type:%";
}

std::string Urma0160BondpImportJettySinglePathJettyOnlySupportUtpO::GetId() const
{
    return "urma_0160";
}
} // namespace diag
