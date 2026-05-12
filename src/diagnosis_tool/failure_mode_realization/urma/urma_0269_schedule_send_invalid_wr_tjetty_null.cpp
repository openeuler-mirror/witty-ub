#include "urma_0269_schedule_send_invalid_wr_tjetty_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0269ScheduleSendInvalidWrTjettyNull> g_urma("urma_0269");

bool Urma0269ScheduleSendInvalidWrTjettyNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid wr->tjetty: NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0269ScheduleSendInvalidWrTjettyNull::GetName() const
{
    return "schedule_send Invalid wr->tjetty: NULL";
}

std::string Urma0269ScheduleSendInvalidWrTjettyNull::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bdp_tjetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0269ScheduleSendInvalidWrTjettyNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0269ScheduleSendInvalidWrTjettyNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0269ScheduleSendInvalidWrTjettyNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid wr->tjetty: NULL";
}

std::string Urma0269ScheduleSendInvalidWrTjettyNull::GetId() const
{
    return "urma_0269";
}
} // namespace diag
