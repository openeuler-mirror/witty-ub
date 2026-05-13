#include "urma_0163_bondp_import_jetty_failed_add_remote_jetty_id_info.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0163BondpImportJettyFailedAddRemoteJettyIdInfo> g_urma("urma_0163");

bool Urma0163BondpImportJettyFailedAddRemoteJettyIdInfo::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to add remote jetty id info"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0163BondpImportJettyFailedAddRemoteJettyIdInfo::GetName() const
{
    return "bondp_import_jetty Failed to add remote jetty id info";
}

std::string Urma0163BondpImportJettyFailedAddRemoteJettyIdInfo::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `add_remote_jetty_id_info(bdp_ctx, bdp_tjetty) != 0`";
}

RootCause Urma0163BondpImportJettyFailedAddRemoteJettyIdInfo::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0163BondpImportJettyFailedAddRemoteJettyIdInfo::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0163BondpImportJettyFailedAddRemoteJettyIdInfo::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to add remote jetty id info";
}

std::string Urma0163BondpImportJettyFailedAddRemoteJettyIdInfo::GetId() const
{
    return "urma_0163";
}
} // namespace diag
