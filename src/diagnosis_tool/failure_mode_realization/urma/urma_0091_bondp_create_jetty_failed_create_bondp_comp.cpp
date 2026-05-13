#include "urma_0091_bondp_create_jetty_failed_create_bondp_comp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0091BondpCreateJettyFailedCreateBondpComp> g_urma("urma_0091");

bool Urma0091BondpCreateJettyFailedCreateBondpComp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create bondp comp"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0091BondpCreateJettyFailedCreateBondpComp::GetName() const
{
    return "bondp_create_jetty Failed to create bondp comp";
}

std::string Urma0091BondpCreateJettyFailedCreateBondpComp::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma0091BondpCreateJettyFailedCreateBondpComp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0091BondpCreateJettyFailedCreateBondpComp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0091BondpCreateJettyFailedCreateBondpComp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create bondp comp";
}

std::string Urma0091BondpCreateJettyFailedCreateBondpComp::GetId() const
{
    return "urma_0091";
}
} // namespace diag
