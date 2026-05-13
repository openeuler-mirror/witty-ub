#include "urma_0152_bondp_delete_pjfs_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0152BondpDeletePjfsResourceDeleteFailure> g_urma("urma_0152");

bool Urma0152BondpDeletePjfsResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete pjfs %, ret: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0152BondpDeletePjfsResourceDeleteFailure::GetName() const
{
    return "bondp_delete_pjfs 删除资源失败";
}

std::string Urma0152BondpDeletePjfsResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "ret";
}

RootCause Urma0152BondpDeletePjfsResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0152BondpDeletePjfsResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0152BondpDeletePjfsResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete pjfs %, ret: %.";
}

std::string Urma0152BondpDeletePjfsResourceDeleteFailure::GetId() const
{
    return "urma_0152";
}
} // namespace diag
