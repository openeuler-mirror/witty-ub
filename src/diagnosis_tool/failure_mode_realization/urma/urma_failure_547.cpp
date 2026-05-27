#include "urma_failure_547.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure547> g_urma("urma_547");

bool UrmaFailure547::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_wait_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Epoll wait err, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure547::GetName() const
{
    return "epoll数据通路处理失败";
}

std::string UrmaFailure547::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure547::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure547::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure547::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_wait_jfc，Epoll wait err, ret:。";
}

std::string UrmaFailure547::GetId() const
{
    return "urma_547";
}

} // namespace diag
