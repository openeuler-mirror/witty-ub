#include "urma_0092_bondp_create_jetty_failed_create_pjetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0092BondpCreateJettyFailedCreatePjetty> g_urma("urma_0092");

bool Urma0092BondpCreateJettyFailedCreatePjetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create pjetty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0092BondpCreateJettyFailedCreatePjetty::GetName() const
{
    return "bondp_create_jetty Failed to create pjetty";
}

std::string Urma0092BondpCreateJettyFailedCreatePjetty::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0092BondpCreateJettyFailedCreatePjetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0092BondpCreateJettyFailedCreatePjetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0092BondpCreateJettyFailedCreatePjetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create pjetty";
}

std::string Urma0092BondpCreateJettyFailedCreatePjetty::GetId() const
{
    return "urma_0092";
}
} // namespace diag
