#include "urma_0108_bondp_create_jfs_failed_create_pjfs.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0108BondpCreateJfsFailedCreatePjfs> g_urma("urma_0108");

bool Urma0108BondpCreateJfsFailedCreatePjfs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create pjfs"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0108BondpCreateJfsFailedCreatePjfs::GetName() const
{
    return "bondp_create_jfs Failed to create pjfs";
}

std::string Urma0108BondpCreateJfsFailedCreatePjfs::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0108BondpCreateJfsFailedCreatePjfs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0108BondpCreateJfsFailedCreatePjfs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0108BondpCreateJfsFailedCreatePjfs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create pjfs";
}

std::string Urma0108BondpCreateJfsFailedCreatePjfs::GetId() const
{
    return "urma_0108";
}
} // namespace diag
