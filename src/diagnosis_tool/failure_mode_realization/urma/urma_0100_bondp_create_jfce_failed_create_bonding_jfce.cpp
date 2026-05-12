#include "urma_0100_bondp_create_jfce_failed_create_bonding_jfce.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0100BondpCreateJfceFailedCreateBondingJfce> g_urma("urma_0100");

bool Urma0100BondpCreateJfceFailedCreateBondingJfce::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create bonding jfce"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0100BondpCreateJfceFailedCreateBondingJfce::GetName() const
{
    return "bondp_create_jfce Failed to create bonding jfce";
}

std::string Urma0100BondpCreateJfceFailedCreateBondingJfce::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma0100BondpCreateJfceFailedCreateBondingJfce::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0100BondpCreateJfceFailedCreateBondingJfce::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0100BondpCreateJfceFailedCreateBondingJfce::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create bonding jfce";
}

std::string Urma0100BondpCreateJfceFailedCreateBondingJfce::GetId() const
{
    return "urma_0100";
}
} // namespace diag
