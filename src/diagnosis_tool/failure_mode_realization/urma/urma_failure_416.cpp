#include "urma_failure_416.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure416> g_urma("urma_416");

bool UrmaFailure416::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_get_async_event' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'bondp get error epoll_event: 0x'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure416::GetName() const
{
    return "epoll数据通路处理失败";
}

std::string UrmaFailure416::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure416::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure416::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure416::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_get_async_event，bondp get error epoll_event: 0x";
}

std::string UrmaFailure416::GetId() const
{
    return "urma_416";
}

} // namespace diag
