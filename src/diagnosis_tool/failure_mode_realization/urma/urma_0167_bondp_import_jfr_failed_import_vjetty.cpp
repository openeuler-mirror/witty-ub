#include "urma_0167_bondp_import_jfr_failed_import_vjetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0167BondpImportJfrFailedImportVjetty> g_urma("urma_0167");

bool Urma0167BondpImportJfrFailedImportVjetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to import vjetty, ["};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0167BondpImportJfrFailedImportVjetty::GetName() const
{
    return "bondp_import_jfr Failed to import vjetty, [";
}

std::string Urma0167BondpImportJfrFailedImportVjetty::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0167BondpImportJfrFailedImportVjetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0167BondpImportJfrFailedImportVjetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0167BondpImportJfrFailedImportVjetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to import vjetty, [";
}

std::string Urma0167BondpImportJfrFailedImportVjetty::GetId() const
{
    return "urma_0167";
}
} // namespace diag
