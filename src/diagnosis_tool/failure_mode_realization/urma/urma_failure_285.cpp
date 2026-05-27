#include "urma_failure_285.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure285> g_urma("urma_285");

bool UrmaFailure285::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Jetty state is wrong in deactive_jetty.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure285::GetName() const
{
    return "Jetty数据通路处理失败";
}

std::string UrmaFailure285::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure285::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure285::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure285::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jetty，Jetty state is wrong in deactive_jetty.。";
}

std::string UrmaFailure285::GetId() const
{
    return "urma_285";
}

} // namespace diag
