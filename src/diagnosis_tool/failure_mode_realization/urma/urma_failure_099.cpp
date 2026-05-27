#include "urma_failure_099.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure099> g_urma("urma_099");

bool UrmaFailure099::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_flush_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to flush pjetty['");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure099::GetName() const
{
    return "物理 Jetty数据通路处理失败";
}

std::string UrmaFailure099::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure099::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure099::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure099::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_flush_jetty，Failed to flush pjetty[";
}

std::string UrmaFailure099::GetId() const
{
    return "urma_099";
}

} // namespace diag
