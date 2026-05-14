#include "urma_failure_648.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure648> g_urma("urma_648");

bool UrmaFailure648::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'schedule_next_recv_port_matrix_singlepath' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid single path port in recv.It is likely because `urma_post_jetty_recv` was called before `urma_bind_jetty`')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure648::GetName() const
{
    return "schedule_next_recv_port_matrix_singlepath 校验 context 无效导致接收流程拒绝继续执行";
}

std::string UrmaFailure648::GetRootCauseDesc() const
{
    return "schedule_next_recv_port_matrix_singlepath 在执行接收前发现调用方传入的 context "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure648::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure648::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure648::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid single path port in recv.It is likely because "
           "`urma_post_jetty_recv` was called before `urma_bind_jetty`";
}

std::string UrmaFailure648::GetId() const
{
    return "urma_648";
}

} // namespace diag
