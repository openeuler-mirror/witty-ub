#include "urma_1007_bondp_import_seg_failed_import_pseg.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1007BondpImportSegFailedImportPseg> g_urma("urma_1007");

bool Urma1007BondpImportSegFailedImportPseg::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to import pseg"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1007BondpImportSegFailedImportPseg::GetName() const
{
    return "bondp_import_seg Failed to import pseg";
}

std::string Urma1007BondpImportSegFailedImportPseg::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma1007BondpImportSegFailedImportPseg::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1007BondpImportSegFailedImportPseg::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1007BondpImportSegFailedImportPseg::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to import pseg";
}

std::string Urma1007BondpImportSegFailedImportPseg::GetId() const
{
    return "urma_1007";
}
} // namespace diag
