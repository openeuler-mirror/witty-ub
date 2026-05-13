#include "urma_0162_bondp_import_jetty_failed_import_pjetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0162BondpImportJettyFailedImportPjetty> g_urma("urma_0162");

bool Urma0162BondpImportJettyFailedImportPjetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to import pjetty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0162BondpImportJettyFailedImportPjetty::GetName() const
{
    return "bondp_import_jetty Failed to import pjetty";
}

std::string Urma0162BondpImportJettyFailedImportPjetty::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0162BondpImportJettyFailedImportPjetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0162BondpImportJettyFailedImportPjetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0162BondpImportJettyFailedImportPjetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to import pjetty";
}

std::string Urma0162BondpImportJettyFailedImportPjetty::GetId() const
{
    return "urma_0162";
}
} // namespace diag
