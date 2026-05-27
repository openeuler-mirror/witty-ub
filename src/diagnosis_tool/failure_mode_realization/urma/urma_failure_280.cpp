#include "urma_failure_280.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure280> g_urma("urma_280");

bool UrmaFailure280::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Jetty state is wrong in active_jetty.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure280::GetName() const
{
    return "Jetty数据通路处理失败";
}

std::string UrmaFailure280::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure280::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure280::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure280::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jetty，Jetty state is wrong in active_jetty.。";
}

std::string UrmaFailure280::GetId() const
{
    return "urma_280";
}

} // namespace diag
