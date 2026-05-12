#include "urma_0271_send_so_from_snd_queue_send_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0271SendSoFromSndQueueSendFailure> g_urma("urma_0271");

bool Urma0271SendSoFromSndQueueSendFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"v_conn has NULL target_vjetty in sending SO"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0271SendSoFromSndQueueSendFailure::GetName() const
{
    return "send_so_from_snd_queue 发送失败";
}

std::string Urma0271SendSoFromSndQueueSendFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `v_conn->target_vjetty == NULL`；该路径返回 URMA_FAIL";
}

RootCause Urma0271SendSoFromSndQueueSendFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0271SendSoFromSndQueueSendFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0271SendSoFromSndQueueSendFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：v_conn has NULL target_vjetty in sending SO";
}

std::string Urma0271SendSoFromSndQueueSendFailure::GetId() const
{
    return "urma_0271";
}
} // namespace diag
