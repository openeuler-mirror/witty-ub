#include "urma_failure_283.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure283> g_urma("urma_283");

bool UrmaFailure283::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Jetty state is wrong in deactive_jetty.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure283::GetName() const
{
    return "Jetty数据通路处理失败";
}

std::string UrmaFailure283::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure283::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure283::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure283::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_deactive_jetty，Jetty state is wrong in deactive_jetty.";
}

std::string UrmaFailure283::GetId() const
{
    return "urma_283";
}

} // namespace diag
