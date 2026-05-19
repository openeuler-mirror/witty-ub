#include "urma_failure_659.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure659> g_urma("urma_659");

bool UrmaFailure659::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'wait_async_event_ack' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'There is an event and it must be acked, acked:' | grep -F ', reported:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure659::GetName() const
{
    return "wait_async_event_ack 处理 context 异常导致当前 URMA 操作失败";
}

std::string UrmaFailure659::GetRootCauseDesc() const
{
    return "wait_async_event_ack 在处理 context "
           "的错误分支输出日志，表示当前对象或下层处理结果已经不能满足继续执行条件，因此返回错误并终止本次 URMA 操作。";
}

RootCause UrmaFailure659::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure659::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure659::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：There is an event and it must be acked, acked:, reported";
}

std::string UrmaFailure659::GetId() const
{
    return "urma_659";
}

} // namespace diag
