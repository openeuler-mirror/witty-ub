#include "urma_1072_schedule_next_recv_port_matrix_singlepath_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1072ScheduleNextRecvPortMatrixSinglepathFailure> g_urma("urma_1072");

bool Urma1072ScheduleNextRecvPortMatrixSinglepathFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid single path port in recv."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1072ScheduleNextRecvPortMatrixSinglepathFailure::GetName() const
{
    return "schedule_next_recv_port_matrix_singlepath 接收失败";
}

std::string Urma1072ScheduleNextRecvPortMatrixSinglepathFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bjetty_ctx->direct_local_port == -1 || bjetty_ctx->direct_target_port == "
           "-1`；该路径返回 URMA_EINVAL";
}

RootCause Urma1072ScheduleNextRecvPortMatrixSinglepathFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1072ScheduleNextRecvPortMatrixSinglepathFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1072ScheduleNextRecvPortMatrixSinglepathFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid single path port in recv.";
}

std::string Urma1072ScheduleNextRecvPortMatrixSinglepathFailure::GetId() const
{
    return "urma_1072";
}
} // namespace diag
