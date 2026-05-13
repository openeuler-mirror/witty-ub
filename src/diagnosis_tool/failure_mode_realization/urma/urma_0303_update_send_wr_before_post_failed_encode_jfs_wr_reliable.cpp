#include "urma_0303_update_send_wr_before_post_failed_encode_jfs_wr_reliable.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0303UpdateSendWrBeforePostFailedEncodeJfsWrReliable> g_urma("urma_0303");

bool Urma0303UpdateSendWrBeforePostFailedEncodeJfsWrReliable::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to encode_jfs_wr_reliable_info"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0303UpdateSendWrBeforePostFailedEncodeJfsWrReliable::GetName() const
{
    return "update_send_wr_before_post Failed to encode_jfs_wr_reliable_inf";
}

std::string Urma0303UpdateSendWrBeforePostFailedEncodeJfsWrReliable::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret != 0`；该路径返回 ret";
}

RootCause Urma0303UpdateSendWrBeforePostFailedEncodeJfsWrReliable::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0303UpdateSendWrBeforePostFailedEncodeJfsWrReliable::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0303UpdateSendWrBeforePostFailedEncodeJfsWrReliable::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to encode_jfs_wr_reliable_info";
}

std::string Urma0303UpdateSendWrBeforePostFailedEncodeJfsWrReliable::GetId() const
{
    return "urma_0303";
}
} // namespace diag
