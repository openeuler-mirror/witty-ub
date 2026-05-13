#include "urma_0231_bondp_flush_jetty_failed_flush_pjetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0231BondpFlushJettyFailedFlushPjetty> g_urma("urma_0231");

bool Urma0231BondpFlushJettyFailedFlushPjetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to flush pjetty[%]: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0231BondpFlushJettyFailedFlushPjetty::GetName() const
{
    return "bondp_flush_jetty Failed to flush pjetty[%]: %";
}

std::string Urma0231BondpFlushJettyFailedFlushPjetty::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `pcr_cnt < 0`；该路径返回 pcr_cnt";
}

RootCause Urma0231BondpFlushJettyFailedFlushPjetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0231BondpFlushJettyFailedFlushPjetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0231BondpFlushJettyFailedFlushPjetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to flush pjetty[%]: %";
}

std::string Urma0231BondpFlushJettyFailedFlushPjetty::GetId() const
{
    return "urma_0231";
}
} // namespace diag
