#include "urma_failure_553.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure553> g_urma("urma_553");

bool UrmaFailure553::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_post_recv_wr_no_store' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Bondp supports at most' | grep -F 'wr_list.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure553::GetName() const
{
    return "WR数据通路处理失败";
}

std::string UrmaFailure553::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure553::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure553::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure553::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_post_recv_wr_no_store，Bondp supports at most，wr_list.";
}

std::string UrmaFailure553::GetId() const
{
    return "urma_553";
}

} // namespace diag
