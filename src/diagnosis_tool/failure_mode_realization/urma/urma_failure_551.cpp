#include "urma_failure_551.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure551> g_urma("urma_551");

bool UrmaFailure551::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'post_send_check_jfs_wr_valid' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'when set cas_wr, either src or dst is NULL.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure551::GetName() const
{
    return "WR数据通路处理失败";
}

std::string UrmaFailure551::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure551::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure551::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure551::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：post_send_check_jfs_wr_valid，when set cas_wr, either src or dst is "
           "NULL.。";
}

std::string UrmaFailure551::GetId() const
{
    return "urma_551";
}

} // namespace diag
