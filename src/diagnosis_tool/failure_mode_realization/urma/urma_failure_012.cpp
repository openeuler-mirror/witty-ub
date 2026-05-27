#include "urma_failure_012.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure012> g_urma("urma_012");

bool UrmaFailure012::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jetty_p_vjetty_info' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to init jetty recv wr buf'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure012::GetName() const
{
    return "Jetty数据通路处理失败";
}

std::string UrmaFailure012::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure012::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure012::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure012::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_del_jetty_p_vjetty_info，Failed to init jetty recv wr buf。";
}

std::string UrmaFailure012::GetId() const
{
    return "urma_012";
}

} // namespace diag
