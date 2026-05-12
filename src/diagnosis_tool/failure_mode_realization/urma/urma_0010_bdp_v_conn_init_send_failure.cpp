#include "urma_0010_bdp_v_conn_init_send_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0010BdpVConnInitSendFailure> g_urma("urma_0010");

bool Urma0010BdpVConnInitSendFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to init sender slide window in bdp_v_conn_table_add"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0010BdpVConnInitSendFailure::GetName() const
{
    return "bdp_v_conn_init 发送失败";
}

std::string Urma0010BdpVConnInitSendFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bdp_slide_wnd_init(&v_conn->send_wnd, BONDP_MAX_BITMAP_SIZE, BONDP_RECV_WND_SIZE, "
           "0)`；该路径返回 0";
}

RootCause Urma0010BdpVConnInitSendFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0010BdpVConnInitSendFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0010BdpVConnInitSendFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to init sender slide window in bdp_v_conn_table_add";
}

std::string Urma0010BdpVConnInitSendFailure::GetId() const
{
    return "urma_0010";
}
} // namespace diag
