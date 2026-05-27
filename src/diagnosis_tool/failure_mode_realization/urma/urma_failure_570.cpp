#include "urma_failure_570.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure570> g_urma("urma_570");

bool UrmaFailure570::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfs or jfc state is wrong in active_jfs.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure570::GetName() const
{
    return "JFS数据通路处理失败";
}

std::string UrmaFailure570::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure570::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure570::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure570::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_active_jfs，jfs or jfc state is wrong in active_jfs.";
}

std::string UrmaFailure570::GetId() const
{
    return "urma_570";
}

} // namespace diag
