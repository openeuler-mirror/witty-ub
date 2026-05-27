#include "urma_failure_097.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure097> g_urma("urma_097");

bool UrmaFailure097::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_post_send_wr_and_store' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'WR->tjetty is NULL'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure097::GetName() const
{
    return "WR数据通路处理失败";
}

std::string UrmaFailure097::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure097::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure097::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure097::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_post_send_wr_and_store，WR->tjetty is NULL。";
}

std::string UrmaFailure097::GetId() const
{
    return "urma_097";
}

} // namespace diag
