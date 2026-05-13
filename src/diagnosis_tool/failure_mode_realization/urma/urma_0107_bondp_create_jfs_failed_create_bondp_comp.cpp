#include "urma_0107_bondp_create_jfs_failed_create_bondp_comp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0107BondpCreateJfsFailedCreateBondpComp> g_urma("urma_0107");

bool Urma0107BondpCreateJfsFailedCreateBondpComp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create bondp comp"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0107BondpCreateJfsFailedCreateBondpComp::GetName() const
{
    return "bondp_create_jfs Failed to create bondp comp";
}

std::string Urma0107BondpCreateJfsFailedCreateBondpComp::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma0107BondpCreateJfsFailedCreateBondpComp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0107BondpCreateJfsFailedCreateBondpComp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0107BondpCreateJfsFailedCreateBondpComp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create bondp comp";
}

std::string Urma0107BondpCreateJfsFailedCreateBondpComp::GetId() const
{
    return "urma_0107";
}
} // namespace diag
