#include "urma_0204_remove_remote_jetty_id_info_failed_del_bdp_r_p2v.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0204RemoveRemoteJettyIdInfoFailedDelBdpRP2v> g_urma("urma_0204");

bool Urma0204RemoveRemoteJettyIdInfoFailedDelBdpRP2v::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to del bdp_r_p2v_vjetty_id[%]: ret: %, jetty_id:"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0204RemoveRemoteJettyIdInfoFailedDelBdpRP2v::GetName() const
{
    return "remove_remote_jetty_id_info Failed to del bdp_r_p2v_vjetty_id[%]";
}

std::string Urma0204RemoveRemoteJettyIdInfoFailedDelBdpRP2v::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret != 0`；该路径返回 ret";
}

RootCause Urma0204RemoveRemoteJettyIdInfoFailedDelBdpRP2v::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0204RemoveRemoteJettyIdInfoFailedDelBdpRP2v::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0204RemoveRemoteJettyIdInfoFailedDelBdpRP2v::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to del bdp_r_p2v_vjetty_id[%]: ret: %, jetty_id:";
}

std::string Urma0204RemoveRemoteJettyIdInfoFailedDelBdpRP2v::GetId() const
{
    return "urma_0204";
}
} // namespace diag
