#include "urma_failure_341.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure341> g_urma("urma_341");

bool UrmaFailure341::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_health_check_ctx' \"$URMA_LOG_PATH\" 2>/dev/null | grep "
        "-F 'Failed to add ctx async fd to health epoll, errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure341::GetName() const
{
    return "context数据通路处理失败";
}

std::string UrmaFailure341::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure341::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure341::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure341::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_health_check_ctx，Failed to add ctx async fd to health "
           "epoll, errno:。";
}

std::string UrmaFailure341::GetId() const
{
    return "urma_341";
}

} // namespace diag
