#include "urma_0109_bondp_create_jfs_failed_create_vjfs.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0109BondpCreateJfsFailedCreateVjfs> g_urma("urma_0109");

bool Urma0109BondpCreateJfsFailedCreateVjfs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create vjfs"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0109BondpCreateJfsFailedCreateVjfs::GetName() const
{
    return "bondp_create_jfs Failed to create vjfs";
}

std::string Urma0109BondpCreateJfsFailedCreateVjfs::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0109BondpCreateJfsFailedCreateVjfs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0109BondpCreateJfsFailedCreateVjfs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0109BondpCreateJfsFailedCreateVjfs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create vjfs";
}

std::string Urma0109BondpCreateJfsFailedCreateVjfs::GetId() const
{
    return "urma_0109";
}
} // namespace diag
