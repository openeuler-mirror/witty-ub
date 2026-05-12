#include "urma_0197_import_pjetty_port_eid_failed_import_direct_tjetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0197ImportPjettyPortEidFailedImportDirectTjetty> g_urma("urma_0197");

bool Urma0197ImportPjettyPortEidFailedImportDirectTjetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to import direct tjetty % %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0197ImportPjettyPortEidFailedImportDirectTjetty::GetName() const
{
    return "import_pjetty_for_port_eid Failed to import direct tjetty % %";
}

std::string Urma0197ImportPjettyPortEidFailedImportDirectTjetty::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0197ImportPjettyPortEidFailedImportDirectTjetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0197ImportPjettyPortEidFailedImportDirectTjetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0197ImportPjettyPortEidFailedImportDirectTjetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to import direct tjetty % %";
}

std::string Urma0197ImportPjettyPortEidFailedImportDirectTjetty::GetId() const
{
    return "urma_0197";
}
} // namespace diag
