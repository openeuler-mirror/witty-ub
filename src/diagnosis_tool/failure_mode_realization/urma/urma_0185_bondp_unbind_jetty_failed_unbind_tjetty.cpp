#include "urma_0185_bondp_unbind_jetty_failed_unbind_tjetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0185BondpUnbindJettyFailedUnbindTjetty> g_urma("urma_0185");

bool Urma0185BondpUnbindJettyFailedUnbindTjetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to unbind tjetty [%](%, %)"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0185BondpUnbindJettyFailedUnbindTjetty::GetName() const
{
    return "bondp_unbind_jetty Failed to unbind tjetty [%](%, %)";
}

std::string Urma0185BondpUnbindJettyFailedUnbindTjetty::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0185BondpUnbindJettyFailedUnbindTjetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0185BondpUnbindJettyFailedUnbindTjetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0185BondpUnbindJettyFailedUnbindTjetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to unbind tjetty [%](%, %)";
}

std::string Urma0185BondpUnbindJettyFailedUnbindTjetty::GetId() const
{
    return "urma_0185";
}
} // namespace diag
