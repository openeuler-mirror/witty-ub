#include "urma_failure_415.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure415> g_urma("urma_415");

bool UrmaFailure415::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_get_async_event' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'epoll_wait no event or err.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure415::GetName() const
{
    return "epoll数据通路处理失败";
}

std::string UrmaFailure415::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure415::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure415::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure415::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_get_async_event，epoll_wait no event or err.";
}

std::string UrmaFailure415::GetId() const
{
    return "urma_415";
}

} // namespace diag
