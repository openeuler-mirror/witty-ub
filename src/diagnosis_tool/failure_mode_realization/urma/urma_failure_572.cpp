#include "urma_failure_572.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure572> g_urma("urma_572");

bool UrmaFailure572::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Jfc state is wrong in active_jfc.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure572::GetName() const
{
    return "JFC数据通路处理失败";
}

std::string UrmaFailure572::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure572::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure572::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure572::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfc，Jfc state is wrong in active_jfc.。";
}

std::string UrmaFailure572::GetId() const
{
    return "urma_572";
}

} // namespace diag
