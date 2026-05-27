#include "urma_failure_549.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure549> g_urma("urma_549");

bool UrmaFailure549::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_post_send_wr_no_store' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Bondp supports at most' | grep -F 'wr_list.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure549::GetName() const
{
    return "WR数据通路处理失败";
}

std::string UrmaFailure549::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure549::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure549::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure549::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_post_send_wr_no_store，Bondp supports at most，wr_list.";
}

std::string UrmaFailure549::GetId() const
{
    return "urma_549";
}

} // namespace diag
