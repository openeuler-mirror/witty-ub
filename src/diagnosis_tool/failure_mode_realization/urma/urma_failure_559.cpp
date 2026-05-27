#include "urma_failure_559.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure559> g_urma("urma_559");

bool UrmaFailure559::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'handle_send_cr_with_store' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to resend jfs wr, wr_id:' | grep -F 'u'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure559::GetName() const
{
    return "JFS数据通路处理失败";
}

std::string UrmaFailure559::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure559::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure559::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure559::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：handle_send_cr_with_store，Failed to resend jfs wr, wr_id:，u";
}

std::string UrmaFailure559::GetId() const
{
    return "urma_559";
}

} // namespace diag
