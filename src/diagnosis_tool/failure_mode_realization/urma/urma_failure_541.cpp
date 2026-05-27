#include "urma_failure_541.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure541> g_urma("urma_541");

bool UrmaFailure541::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_wait_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Epoll wait err, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure541::GetName() const
{
    return "epoll数据通路处理失败";
}

std::string UrmaFailure541::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure541::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure541::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure541::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_wait_jfc，Epoll wait err, ret:";
}

std::string UrmaFailure541::GetId() const
{
    return "urma_541";
}

} // namespace diag
