#include "urma_0118_bondp_create_pjfs_failed_create_pjfs.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0118BondpCreatePjfsFailedCreatePjfs> g_urma("urma_0118");

bool Urma0118BondpCreatePjfsFailedCreatePjfs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create pjfs %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0118BondpCreatePjfsFailedCreatePjfs::GetName() const
{
    return "bondp_create_pjfs Failed to create pjfs %.";
}

std::string Urma0118BondpCreatePjfsFailedCreatePjfs::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0118BondpCreatePjfsFailedCreatePjfs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0118BondpCreatePjfsFailedCreatePjfs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0118BondpCreatePjfsFailedCreatePjfs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create pjfs %.";
}

std::string Urma0118BondpCreatePjfsFailedCreatePjfs::GetId() const
{
    return "urma_0118";
}
} // namespace diag
