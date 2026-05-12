#include "urma_0073_add_remote_jetty_id_info_failed_add_bdp_r_p2v.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0073AddRemoteJettyIdInfoFailedAddBdpRP2v> g_urma("urma_0073");

bool Urma0073AddRemoteJettyIdInfoFailedAddBdpRP2v::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to add bdp_r_p2v_vjetty_id[%]: ret: %, jetty_id:"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0073AddRemoteJettyIdInfoFailedAddBdpRP2v::GetName() const
{
    return "add_remote_jetty_id_info Failed to add bdp_r_p2v_vjetty_id[%]";
}

std::string Urma0073AddRemoteJettyIdInfoFailedAddBdpRP2v::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret != 0`；该路径返回 -1";
}

RootCause Urma0073AddRemoteJettyIdInfoFailedAddBdpRP2v::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0073AddRemoteJettyIdInfoFailedAddBdpRP2v::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0073AddRemoteJettyIdInfoFailedAddBdpRP2v::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to add bdp_r_p2v_vjetty_id[%]: ret: %, jetty_id:";
}

std::string Urma0073AddRemoteJettyIdInfoFailedAddBdpRP2v::GetId() const
{
    return "urma_0073";
}
} // namespace diag
