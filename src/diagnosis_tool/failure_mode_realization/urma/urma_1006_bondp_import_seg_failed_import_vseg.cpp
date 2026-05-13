#include "urma_1006_bondp_import_seg_failed_import_vseg.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1006BondpImportSegFailedImportVseg> g_urma("urma_1006");

bool Urma1006BondpImportSegFailedImportVseg::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to import vseg"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1006BondpImportSegFailedImportVseg::GetName() const
{
    return "bondp_import_seg Failed to import vseg";
}

std::string Urma1006BondpImportSegFailedImportVseg::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma1006BondpImportSegFailedImportVseg::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1006BondpImportSegFailedImportVseg::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1006BondpImportSegFailedImportVseg::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to import vseg";
}

std::string Urma1006BondpImportSegFailedImportVseg::GetId() const
{
    return "urma_1006";
}
} // namespace diag
