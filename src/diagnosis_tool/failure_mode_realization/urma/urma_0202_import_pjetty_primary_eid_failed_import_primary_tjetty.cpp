#include "urma_0202_import_pjetty_primary_eid_failed_import_primary_tjetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0202ImportPjettyPrimaryEidFailedImportPrimaryTjetty> g_urma("urma_0202");

bool Urma0202ImportPjettyPrimaryEidFailedImportPrimaryTjetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to import primary tjetty % %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0202ImportPjettyPrimaryEidFailedImportPrimaryTjetty::GetName() const
{
    return "import_pjetty_for_primary_eid Failed to import primary tjetty % %";
}

std::string Urma0202ImportPjettyPrimaryEidFailedImportPrimaryTjetty::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0202ImportPjettyPrimaryEidFailedImportPrimaryTjetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0202ImportPjettyPrimaryEidFailedImportPrimaryTjetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0202ImportPjettyPrimaryEidFailedImportPrimaryTjetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to import primary tjetty % %";
}

std::string Urma0202ImportPjettyPrimaryEidFailedImportPrimaryTjetty::GetId() const
{
    return "urma_0202";
}
} // namespace diag
