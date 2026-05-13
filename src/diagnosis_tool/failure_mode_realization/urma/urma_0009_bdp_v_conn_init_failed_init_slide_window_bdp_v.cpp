#include "urma_0009_bdp_v_conn_init_failed_init_slide_window_bdp_v.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0009BdpVConnInitFailedInitSlideWindowBdpV> g_urma("urma_0009");

bool Urma0009BdpVConnInitFailedInitSlideWindowBdpV::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to init slide window in bdp_v_conn_table_add"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0009BdpVConnInitFailedInitSlideWindowBdpV::GetName() const
{
    return "bdp_v_conn_init Failed to init slide window in bdp_v";
}

std::string Urma0009BdpVConnInitFailedInitSlideWindowBdpV::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bdp_slide_wnd_init(&v_conn->recv_wnd, BONDP_MAX_BITMAP_SIZE, BONDP_RECV_WND_SIZE, "
           "0)`；该路径返回 -1";
}

RootCause Urma0009BdpVConnInitFailedInitSlideWindowBdpV::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0009BdpVConnInitFailedInitSlideWindowBdpV::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0009BdpVConnInitFailedInitSlideWindowBdpV::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to init slide window in bdp_v_conn_table_add";
}

std::string Urma0009BdpVConnInitFailedInitSlideWindowBdpV::GetId() const
{
    return "urma_0009";
}
} // namespace diag
