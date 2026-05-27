#include "urma_failure_010.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure010> g_urma("urma_010");

bool UrmaFailure010::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jetty_p_vjetty_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to init jetty send wr buf'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure010::GetName() const
{
    return "Jetty数据通路处理失败";
}

std::string UrmaFailure010::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure010::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure010::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure010::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_del_jetty_p_vjetty_info，Failed to init jetty send wr buf";
}

std::string UrmaFailure010::GetId() const
{
    return "urma_010";
}

} // namespace diag
