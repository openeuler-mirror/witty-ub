#include "urma_failure_571.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure571> g_urma("urma_571");

bool UrmaFailure571::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_health_calc_primary_interval_us' \"$URMA_LOG_PATH\" 2>/dev/null "
        "| grep -F 'Health check epoll_wait failed, errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure571::GetName() const
{
    return "健康检查数据通路处理失败";
}

std::string UrmaFailure571::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure571::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure571::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure571::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_health_calc_primary_interval_us，Health check epoll_wait failed, "
           "errno:。";
}

std::string UrmaFailure571::GetId() const
{
    return "urma_571";
}

} // namespace diag
