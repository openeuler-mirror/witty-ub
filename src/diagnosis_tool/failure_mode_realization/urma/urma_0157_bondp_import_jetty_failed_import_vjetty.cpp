#include "urma_0157_bondp_import_jetty_failed_import_vjetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0157BondpImportJettyFailedImportVjetty> g_urma("urma_0157");

bool Urma0157BondpImportJettyFailedImportVjetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to import vjetty, ["};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0157BondpImportJettyFailedImportVjetty::GetName() const
{
    return "bondp_import_jetty Failed to import vjetty, [";
}

std::string Urma0157BondpImportJettyFailedImportVjetty::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0157BondpImportJettyFailedImportVjetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0157BondpImportJettyFailedImportVjetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0157BondpImportJettyFailedImportVjetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to import vjetty, [";
}

std::string Urma0157BondpImportJettyFailedImportVjetty::GetId() const
{
    return "urma_0157";
}
} // namespace diag
