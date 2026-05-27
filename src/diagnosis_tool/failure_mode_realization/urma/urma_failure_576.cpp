#include "urma_failure_576.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure576> g_urma("urma_576");

bool UrmaFailure576::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'jfs or jfc state is wrong in active_jfs.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure576::GetName() const
{
    return "JFS数据通路处理失败";
}

std::string UrmaFailure576::GetRootCauseDesc() const
{
    return "函数处理URMA数据收发路径，需要完成WR转换、投递、完成事件处理或重传，相关对象状态或下层操作失败导致数据通路"
           "中断。";
}

RootCause UrmaFailure576::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure576::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure576::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfs，jfs or jfc state is wrong in active_jfs.。";
}

std::string UrmaFailure576::GetId() const
{
    return "urma_576";
}

} // namespace diag
