#include "urma_failure_554.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure554> g_urma("urma_554");

bool UrmaFailure554::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_post_recv_wr_and_store' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to copy jfr wr'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure554::GetName() const
{
    return "JFR数据通路处理失败";
}

std::string UrmaFailure554::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure554::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure554::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure554::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_post_recv_wr_and_store，Failed to copy jfr wr";
}

std::string UrmaFailure554::GetId() const
{
    return "urma_554";
}

} // namespace diag
