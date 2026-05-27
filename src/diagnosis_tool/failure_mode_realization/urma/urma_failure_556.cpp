#include "urma_failure_556.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure556> g_urma("urma_556");

bool UrmaFailure556::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_post_send_wr_and_store' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to copy jfs wr'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure556::GetName() const
{
    return "JFS数据通路处理失败";
}

std::string UrmaFailure556::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure556::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure556::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure556::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_post_send_wr_and_store，Failed to copy jfs wr。";
}

std::string UrmaFailure556::GetId() const
{
    return "urma_556";
}

} // namespace diag
